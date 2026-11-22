import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import httpx

for candidate_env in [
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]:
    if candidate_env.exists():
        load_dotenv(candidate_env, override=False)


SYSTEM_PROMPT = """You are CivicPilot RAG Assistant for the PM-KISAN scheme.
Answer the citizen's question ONLY using the retrieved clauses provided in the context.
Every substantive claim in your answer must cite the clause ID (e.g., [PMK-G-4.2]).
If the retrieved clauses do NOT contain sufficient information to answer the question accurately, or if the question is out of scope / not covered by the PM-KISAN corpus:
- You MUST set needs_escalation to true.
- State clearly that the matter requires escalation to an official nodal officer or helpdesk.
- Do NOT hallucinate or extrapolate beyond the provided text.
Output your response strictly as JSON with the fields:
- answer: string (in the requested language: {lang})
- citations: list of {id, text} of the specific clauses cited
- confidence: float between 0.0 and 1.0
- needs_escalation: boolean"""


class GeminiClient:
    """Client for Gemini Embeddings and Generation with robust offline/mock fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.is_live = bool(
            self.api_key
            and self.api_key != "your_gemini_api_key_here"
            and not self.api_key.startswith("dummy")
        )
        self.embedding_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
        )
        self.generate_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        )

    def _fallback_embedding(self, text: str, dim: int = 128) -> List[float]:
        """Deterministic pseudo-embedding based on hashed n-grams and bag-of-words for offline/test mode."""
        words = re.findall(r"\w+", text.lower())
        vec = [0.0] * dim
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h // dim) % 2 == 0 else -1.0
            vec[idx] += sign

        # Add 2-gram hashes for phrase matching
        for i in range(len(words) - 1):
            bg = f"{words[i]}_{words[i+1]}"
            h = int(hashlib.md5(bg.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h // dim) % 2 == 0 else -1.0
            vec[idx] += sign * 1.5

        # L2-normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-6:
            vec = [v / norm for v in vec]
        return vec

    def get_embedding(self, text: str) -> List[float]:
        """Fetches Gemini embedding (text-embedding-004) or deterministic fallback."""
        if not self.is_live:
            return self._fallback_embedding(text)

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    f"{self.embedding_url}?key={self.api_key}",
                    json={
                        "model": "models/text-embedding-004",
                        "content": {"parts": [{"text": text[:2000]}]},
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("embedding", {}).get("values", self._fallback_embedding(text))
        except Exception:
            pass

        return self._fallback_embedding(text)

    def generate_answer(
        self,
        question: str,
        retrieved_clauses: List[Dict[str, Any]],
        lang: str = "en",
    ) -> Dict[str, Any]:
        """Answers strictly based on retrieved clauses using Gemini or deterministic fallback engine."""
        lang_map = {
            "en": "English",
            "hi": "Hindi",
            "pa": "Punjabi",
            "mr": "Marathi",
            "te": "Telugu",
            "ta": "Tamil",
            "bn": "Bengali",
            "gu": "Gujarati",
            "kn": "Kannada",
        }
        lang_full = lang_map.get(lang, "English")
        formatted_system = SYSTEM_PROMPT.replace("{lang}", f"{lang_full} ({lang})")

        # If live Gemini API is configured, call Gemini
        if self.is_live:
            try:
                context_blocks = "\n\n".join(
                    f"Clause [{c['id']}] - {c.get('title', '')}:\n{c['text']}"
                    for c in retrieved_clauses
                )
                user_content = f"CONTEXT CLAUSES:\n{context_blocks}\n\nUSER QUESTION:\n{question}\n\nLANGUAGE:\n{lang}"

                payload = {
                    "contents": [
                        {"role": "user", "parts": [{"text": f"{formatted_system}\n\n{user_content}"}]}
                    ],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    },
                }

                with httpx.Client(timeout=15.0) as client:
                    res = client.post(
                        f"{self.generate_url}?key={self.api_key}",
                        json=payload,
                    )
                    if res.status_code == 200:
                        content_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(content_text)
                        return {
                            "answer": parsed.get("answer", ""),
                            "citations": parsed.get("citations", []),
                            "confidence": float(parsed.get("confidence", 0.0)),
                            "needs_escalation": bool(parsed.get("needs_escalation", False)),
                        }
            except Exception:
                # Fall through to fallback engine if live call fails
                pass

        # Deterministic answering engine for offline mode / tests
        return self._deterministic_answer(question, retrieved_clauses, lang)

    def _deterministic_answer(
        self,
        question: str,
        retrieved_clauses: List[Dict[str, Any]],
        lang: str = "en",
    ) -> Dict[str, Any]:
        """Deterministic rule/retrieval evaluator ensuring strict grounding and escalation."""
        q_lower = question.lower()

        # Check explicit out-of-scope triggers (e.g. mudra loan, tractor commercial subsidy, crypto trading)
        out_of_scope_keywords = [
            "mudra",
            "crypto",
            "bitcoin",
            "commercial tractor",
            "tractor subsidy",
            "personal loan",
            "stock market",
            "gold loan",
        ]
        out_of_scope_msgs = {
            "en": "This question is not covered by the PM-KISAN guidelines and requires escalation to an official nodal officer.",
            "hi": "यह विषय पीएम-किसान योजना के दिशा-निर्देशों में शामिल नहीं है और इसके लिए संबंधित अधिकारी से संपर्क करने की आवश्यकता है।",
            "pa": "ਇਹ ਵਿਸ਼ਾ ਪੀਐੱਮ-ਕਿਸਾਨ ਸਕੀਮ ਦੇ ਦਿਸ਼ਾ-ਨਿਰਦੇਸ਼ਾਂ ਵਿੱਚ ਸ਼ਾਮਲ ਨਹੀਂ ਹੈ ਅਤੇ ਅਧਿਕਾਰੀ ਕੋਲ ਪਹੁੰਚ ਦੀ ਲੋੜ ਹੈ।",
            "mr": "हा विषय पीएम-किसान योजनेच्या मार्गदर्शक तत्त्वांमध्ये समाविष्ट नाही आणि यासाठी अधिकाऱ्यांशी संपर्क साधणे आवश्यक आहे.",
            "te": "ఈ అంశం పీఎం-కిసాన్ పథకం మార్గదర్శకాల పరిధిలోకి రాదు మరియు అధికారిక నోడల్ అధికారికి నివేదించవలసి ఉంటుంది.",
            "ta": "இந்தக் கேள்வி பிஎம்-கிசான் திட்ட வழிகாட்டுதல்களில் இல்லை, எனவே நோடல் அதிகாரியிடம் முறையிட வேண்டும்.",
            "bn": "এই বিষয়টি পিএম-কিসান নির্দেশিকায় অন্তর্ভুক্ত নয় এবং এর জন্য নোডাল অফিসারের সাথে যোগাযোগ করা প্রয়োজন।",
            "gu": "આ વિષય પીએમ-કિસાન યોજનાની માર્ગદર્શિકામાં આવતો નથી અને તેના માટે નોડલ અધિકારીનો સંપર્ક કરવો જરૂરી છે.",
            "kn": "ಈ ವಿಷಯವು ಪಿಎಂ-ಕಿಸಾನ್ ಯೋಜನೆಯ ಮಾರ್ಗಸೂಚಿಗಳಲ್ಲಿ ಒಳಗೊಂಡಿಲ್ಲ ಮತ್ತು ನೋಡಲ್ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸುವುದು ಅಗತ್ಯವಾಗಿದೆ.",
        }
        if any(kw in q_lower for kw in out_of_scope_keywords):
            return {
                "answer": out_of_scope_msgs.get(lang, out_of_scope_msgs["en"]),
                "citations": [],
                "confidence": 0.0,
                "needs_escalation": True,
            }

        not_covered_msgs = {
            "en": "No relevant clauses found in the PM-KISAN corpus to answer this query. This matter requires escalation.",
            "hi": "पीएम-किसान नियमों में इस प्रश्न से संबंधित कोई खंड नहीं मिला। कृपया नोडल अधिकारी से संपर्क करें।",
            "pa": "ਪੀਐੱਮ-ਕਿਸਾਨ ਨਿਯਮਾਂ ਵਿੱਚ ਇਸ ਸਵਾਲ ਨਾਲ ਸੰਬੰਧਿਤ ਕੋਈ ਧਾਰਾ ਨਹੀਂ ਮਿਲੀ। ਕਿਰਪਾ ਕਰਕੇ ਨੋਡਲ ਅਧਿਕਾਰੀ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
            "mr": "पीएम-किसान नियमावलीत या प्रश्नाशी संबंधित कोणताही नियम आढळला नाही. कृपया नोडल अधिकाऱ्यांशी संपर्क साधा.",
            "te": "పీఎం-కిసాన్ నిబంధనలలో ఈ ప్రశ్నకు సంబంధించిన క్లాజ్ కనుగొనబడలేదు. దయచేసి నోడల్ అధికారిని సంప్రదించండి.",
            "ta": "பிஎம்-கிசான் விதிகளில் இந்தக் கேள்விக்குரிய பிரிவு எதுவும் காணப்படவில்லை. தயவுசெய்து அதிகாரியை அணுகவும்.",
            "bn": "পিএম-কিসান নিয়মে এই প্রশ্নের সাথে সম্পর্কিত কোনো ধারা পাওয়া যায়নি। অনুগ্রহ করে নোডাল অফিসারের সাথে যোগাযোগ করুন।",
            "gu": "પીએમ-કિસાન નિયમોમાં આ પ્રશ્નને લગતો કોઈ નિયમ મળ્યો નથી. કૃપા કરીને નોડલ અધિકારીનો સંપર્ક કરો.",
            "kn": "ಪಿಎಂ-ಕಿಸಾನ್ ನಿಯಮಗಳಲ್ಲಿ ಈ ಪ್ರಶ್ನೆಗೆ ಸಂಬಂಧಿಸಿದ ಯಾವುದೇ ನಿಯಮ ಕಂಡುಬಂದಿಲ್ಲ. ದಯವಿಟ್ಟು ನೋಡಲ್ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        }
        if not retrieved_clauses:
            return {
                "answer": not_covered_msgs.get(lang, not_covered_msgs["en"]),
                "citations": [],
                "confidence": 0.0,
                "needs_escalation": True,
            }

        # Check relevance of top chunk
        top_chunk = retrieved_clauses[0]
        top_text_lower = top_chunk["text"].lower()

        # Extract words from question ignoring common stopwords
        stopwords = {"what", "who", "is", "are", "the", "for", "under", "in", "and", "how", "can", "a", "an", "to", "by", "of"}
        q_words = [w for w in re.findall(r"\w+", q_lower) if w not in stopwords and len(w) > 2]

        overlap = sum(1 for w in q_words if w in top_text_lower)
        relevance_ratio = overlap / max(len(q_words), 1)

        # If overlap is very weak (< 0.25), escalate
        if relevance_ratio < 0.25:
            return {
                "answer": (
                    "उपलब्ध पीएम-किसान खंडों में इस प्रश्न के लिए पर्याप्त जानकारी नहीं है। इसे नोडल अधिकारी को अग्रेषित किया जाना चाहिए।"
                    if lang == "hi"
                    else "The retrieved clauses do not contain sufficient information to answer this question accurately. This matter requires escalation."
                ),
                "citations": [],
                "confidence": 0.1,
                "needs_escalation": True,
            }

        # Select relevant citations
        citations = []
        for c in retrieved_clauses[:2]:
            c_overlap = sum(1 for w in q_words if w in c["text"].lower())
            if c_overlap > 0:
                citations.append({"id": c["id"], "text": c["text"]})

        if not citations:
            citations = [{"id": top_chunk["id"], "text": top_chunk["text"]}]

        cited_ids = ", ".join(f"[{c['id']}]" for c in citations)

        # Synthesize concise grounded answer
        if lang == "hi":
            answer = f"खंड {cited_ids} के अनुसार: {top_chunk['title']}। {top_chunk['text'][:250]}..."
        else:
            answer = f"According to {cited_ids}: under {top_chunk['title']}, {top_chunk['text']}"

        return {
            "answer": answer,
            "citations": citations,
            "confidence": 0.95,
            "needs_escalation": False,
        }
