import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from rag.gemini import GeminiClient
from rules.engine import evaluate_profile


FIELD_QUESTIONS = [
    {
        "field": "owns_cultivable_land",
        "type": "boolean",
        "en": "Does your family own cultivable agricultural land in your name?",
        "hi": "क्या आपके या आपके परिवार के नाम पर खेती योग्य कृषि भूमि है?",
        "pa": "ਕੀ ਤੁਹਾਡੇ ਜਾਂ ਤੁਹਾਡੇ ਪਰਿਵਾਰ ਦੇ ਨਾਮ 'ਤੇ ਖੇਤੀ ਯੋਗ ਜ਼ਮੀਨ ਹੈ?",
        "mr": "तुमच्या किंवा तुमच्या कुटुंबाच्या नावावर शेतीयोग्य जमीन आहे का?",
        "te": "మీ లేదా మీ కుటుంబం పేరు మీద సాగు చేయదగిన వ్యవసాయ భూమి ఉందా?",
        "ta": "உங்கள் அல்லது உங்கள் குடும்பத்தின் பெயரில் சாகுபடி செய்யக்கூடிய நிலம் உள்ளதா?",
        "bn": "আপনার বা আপনার পরিবারের নামে কি চাষযোগ্য কৃষিজমি আছে?",
        "gu": "શું તમારા અથવા તમારા પરિવારના નામે ખેતીલાયક જમીન છે?",
        "kn": "ನಿಮ್ಮ ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದ ಹೆಸರಿನಲ್ಲಿ ಕೃಷಿ ಯೋಗ್ಯ ಜಮೀನು ಇದೆಯೇ?",
    },
    {
        "field": "land_area_hectares",
        "type": "float",
        "en": "How much cultivable land do you own in hectares? (e.g. 1.5, or enter in acres)",
        "hi": "आपके पास कुल कितनी कृषि भूमि है (हेक्टेयर में, उदा. 1.5)?",
        "pa": "ਤੁਹਾਡੇ ਕੋਲ ਕੁੱਲ ਕਿੰਨੀ ਖੇਤੀ ਯੋਗ ਜ਼ਮੀਨ ਹੈ (ਹੈਕਟੇਅਰ ਵਿੱਚ, ਜਿਵੇਂ 1.5)?",
        "mr": "तुमच्याकडे एकूण किती शेतीजमीन आहे (हेक्टरमध्ये, उदा. 1.5)?",
        "te": "మీ వద్ద మొత్తం ఎంత వ్యవసాయ భూమి ఉంది (హెక్టార్లలో, ఉదా. 1.5)?",
        "ta": "உங்களிடம் மொத்தம் எவ்வளவு விவசாய நிலம் உள்ளது (ஹெக்டேரில், எ.கா. 1.5)?",
        "bn": "আপনার মোট কত কৃষিজমি আছে (হেক্টরে, যেমন ১.৫)?",
        "gu": "તમારી પાસે કુલ કેટલી ખેતીની જમીન છે (હેક્ટરમાં, દા.ત. 1.5)?",
        "kn": "ನಿಮ್ಮ ಬಳಿ ಒಟ್ಟು ಎಷ್ಟು ಕೃಷಿ ಜಮೀನು ಇದೆ (ಹೆಕ್ಟೇರ್‌ಗಳಲ್ಲಿ, ಉದಾ. 1.5)?",
    },
    {
        "field": "land_record_seeded",
        "type": "boolean",
        "en": "Is your land record (Bhulekh / Khatauni) digitally verified and seeded on the state portal?",
        "hi": "क्या आपका भूमि रिकॉर्ड (भूलेख/खतौनी) राज्य पोर्टल पर ऑनलाइन सत्यापित और दर्ज है?",
        "pa": "ਕੀ ਤੁਹਾਡਾ ਜ਼ਮੀਨੀ ਰਿਕਾਰਡ (ਜਮ੍ਹਾਂਬੰਦੀ) ਸਰਕਾਰੀ ਪੋਰਟਲ 'ਤੇ ਡਿਜੀਟਲ ਤੌਰ 'ਤੇ ਤਸਦੀਕ ਹੈ?",
        "mr": "तुमचा जमीन महसूल अभिलेख (७/१२ उतारा / भूलेख) ऑनलाइन पडताळलेला आहे का?",
        "te": "మీ భూమి రికార్డు (పట్టాదారు పాస్‌బుక్ / ధరణి) ఆన్‌లైన్‌లో ధృవీకరించబడిందా?",
        "ta": "உங்கள் நில ஆவணம் (பட்டா / சிட்டா) அரசு இணையதளத்தில் சரிபார்க்கப்பட்டுள்ளதா?",
        "bn": "আপনার জমির খতিয়ান রেকর্ড কি সরকারি পোর্টালে ডিজিটালভাবে যাচাই করা আছে?",
        "gu": "શું તમારો જમીન રેકોર્ડ (૭/૧૨ અને ૮-અ) રાજ્ય પોર્ટલ પર ડિજિટલી લિંક છે?",
        "kn": "ನಿಮ್ಮ ಜಮೀನಿನ ಪಹಣಿ (RTC) ಸರ್ಕಾರಿ ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಡಿಜಿಟಲ್ ಆಗಿ ಪರಿಶೀಲಿಸಲಾಗಿದೆಯೇ?",
    },
    {
        "field": "aadhaar_seeded",
        "type": "boolean",
        "en": "Is your Aadhaar number linked and seeded with your bank account via NPCI for DBT?",
        "hi": "क्या आपका आधार नंबर आपके बैंक खाते से लिंक और एनपीसीआई (NPCI) मैप है?",
        "pa": "ਕੀ ਤੁਹਾਡਾ ਆਧਾਰ ਨੰਬਰ ਬੈਂਕ ਖਾਤੇ ਨਾਲ NPCI ਰਾਹੀਂ ਲਿੰਕ ਹੈ?",
        "mr": "तुमचा आधार क्रमांक बँक खात्याशी NPCI मॅपिंगद्वारे लिंक आहे का?",
        "te": "మీ ఆధార్ నంబర్ మీ బ్యాంక్ ఖాతాకు NPCI మ్యాపింగ్ ద్వారా లింక్ చేయబడిందా?",
        "ta": "உங்கள் ஆதார் எண் வங்கி கணக்குடன் NPCI மூலம் இணைக்கப்பட்டுள்ளதா?",
        "bn": "আপনার আধার নম্বর কি ব্যাংক অ্যাকাউন্টের সাথে NPCI ডিবিটি লিঙ্ক করা আছে?",
        "gu": "શું તમારો આધાર નંબર બેંક ખાતા સાથે NPCI મેપિંગ દ્વારા જોડાયેલો છે?",
        "kn": "ನಿಮ್ಮ ಆಧಾರ್ ಸಂಖ್ಯೆ ಬ್ಯಾಂಕ್ ಖಾತೆಗೆ NPCI ಮೂಲಕ ಲಿಂಕ್ ಆಗಿದೆಯೇ?",
    },
    {
        "field": "ekyc_completed",
        "type": "boolean",
        "en": "Have you completed biometric fingerprint or OTP e-KYC on the PM-KISAN portal or CSC?",
        "hi": "क्या आपने पीएम-किसान पोर्टल या सीएससी केंद्र पर बायोमेट्रिक या ओटीपी ई-केवाईसी (e-KYC) पूरा कर लिया है?",
        "pa": "ਕੀ ਤੁਸੀਂ ਪੀਐੱਮ-ਕਿਸਾਨ ਪੋਰਟਲ ਜਾਂ CSC 'ਤੇ ਬਾਇਓਮੈਟ੍ਰਿਕ ਜਾਂ OTP ਈ-ਕੇਵਾਈਸੀ ਪੂਰਾ ਕਰ ਲਿਆ ਹੈ?",
        "mr": "तुम्ही पीएम-किसान पोर्टलवर किंवा CSC केंद्रावर बायोमेट्रिक किंवा OTP ई-केवायसी पूर्ण केले आहे का?",
        "te": "మీరు పీఎం-కిసాన్ పోర్టల్‌లో లేదా CSC కేంద్రంలో బయోమెట్రిక్ లేదా OTP ఇ-కేవైసీ పూర్తి చేశారా?",
        "ta": "பிஎம்-கிசான் இணையதளம் அல்லது CSC மையத்தில் பயோமெட்ரிக் இ-கேஒய்சி முடித்துவிட்டீர்களா?",
        "bn": "আপনি কি পিএম-কিসান পোর্টালে বা CSC কেন্দ্রে বায়োমেট্রিক বা ওটিপি ই-কেওয়াইসি সম্পন্ন করেছেন?",
        "gu": "શું તમે પીએમ-કિસાન પોર્ટલ અથવા CSC સેન્ટર પર બાયોમેટ્રિક અથવા OTP ઈ-કેવાયસી પૂર્ણ કર્યું છે?",
        "kn": "ನೀವು ಪಿಎಂ-ಕಿಸಾನ್ ಪೋರ್ಟಲ್ ಅಥವಾ ಸಿಎಸ್‌ಸಿ ಕೇಂದ್ರದಲ್ಲಿ ಬಯೋಮೆಟ್ರಿಕ್ ಅಥವಾ ಒಟಿಪಿ ಇ-ಕೆವೈಸಿ ಪೂರ್ಣಗೊಳಿಸಿದ್ದೀರಾ?",
    },
    {
        "field": "bank_account_dbt_active",
        "type": "boolean",
        "en": "Is your bank account active and enabled to receive Direct Benefit Transfer (DBT) payments?",
        "hi": "क्या आपका बैंक खाता सक्रिय है और प्रत्यक्ष लाभ अंतरण (DBT) प्राप्त करने के लिए चालू है?",
        "pa": "ਕੀ ਤੁਹਾਡਾ ਬੈਂਕ ਖਾਤਾ ਸਰਗਰਮ ਹੈ ਅਤੇ DBT ਭੁਗਤਾਨ ਪ੍ਰਾਪਤ ਕਰਨ ਲਈ ਚਾਲੂ ਹੈ?",
        "mr": "तुमचे बँक खाते सक्रिय असून प्रत्यक्ष लाभ हस्तांतरण (DBT) मिळवण्यासाठी चालू आहे का?",
        "te": "మీ బ్యాంక్ ఖాతా సక్రియంగా ఉండి DBT నగదు బదిలీకి సిద్ధంగా ఉందా?",
        "ta": "உங்கள் வங்கி கணக்கு செயல்பாட்டில் உள்ளதா மற்றும் DBT பெற தகுதியுள்ளதா?",
        "bn": "আপনার ব্যাংক অ্যাকাউন্ট কি সক্রিয় এবং ডিবিটি টাকা পাওয়ার জন্য প্রস্তুত?",
        "gu": "શું તમારું બેંક ખાતું સક્રિય છે અને DBT સહાય મેળવવા માટે ચાલુ છે?",
        "kn": "ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆ ಸಕ್ರಿಯವಾಗಿದ್ದು ಡಿಬಿಟಿ ಹಣ ಪಡೆಯಲು ಸಿದ್ಧವಾಗಿದೆಯೇ?",
    },
    {
        "field": "is_institutional_landholder",
        "type": "boolean",
        "en": "Is the agricultural land owned by an institution, trust, or company?",
        "hi": "क्या यह कृषि भूमि किसी संस्था, ट्रस्ट या कंपनी के नाम पर है?",
        "pa": "ਕੀ ਇਹ ਖੇਤੀ ਜ਼ਮੀਨ ਕਿਸੇ ਸੰਸਥਾ, ਟਰੱਸਟ ਜਾਂ ਕੰਪਨੀ ਦੇ ਨਾਮ 'ਤੇ ਹੈ?",
        "mr": "ही शेतजमीन कोणत्याही संस्था, ट्रस्ट किंवा कंपनीच्या नावावर आहे का?",
        "te": "ఈ వ్యవసాయ భూమి ఏదైనా సంస్థ, ట్రస్ట్ లేదా కంపెనీ పేరిట ఉందా?",
        "ta": "இந்த விவசாய நிலம் ஏதேனும் நிறுவனம், அறக்கட்டளை அல்லது நிறுவனத்தின் பெயரில் உள்ளதா?",
        "bn": "এই কৃষিজমি কি কোনো প্রতিষ্ঠান, ট্রাস্ট বা কোম্পানির নামে রয়েছে?",
        "gu": "શું આ ખેતીની જમીન કોઈ સંસ્થા, ટ્રસ્ટ કે કંપનીના નામે છે?",
        "kn": "ಈ ಕೃಷಿ ಜಮೀನು ಯಾವುದೇ ಸಂಸ್ಥೆ, ಟ್ರಸ್ಟ್ ಅಥವಾ ಕಂಪನಿಯ ಹೆಸರಿನಲ್ಲಿದೆಯೇ?",
    },
    {
        "field": "is_constitutional_post_holder",
        "type": "boolean",
        "en": "Has any member of your family ever held a constitutional post (such as MP, MLA, Minister, or Mayor)?",
        "hi": "क्या आपके परिवार के किसी सदस्य ने कभी कोई संवैधानिक पद (जैसे सांसद, विधायक, मंत्री या महापौर) संभाला है?",
        "pa": "ਕੀ ਤੁਹਾਡੇ ਪਰਿਵਾਰ ਦੇ ਕਿਸੇ ਮੈਂਬਰ ਨੇ ਕਦੇ ਸੰਵਿਧਾਨਕ ਅਹੁਦਾ (ਜਿਵੇਂ ਸੰਸਦ ਮੈਂਬਰ, ਵਿਧਾਇਕ, ਮੰਤਰੀ) ਸੰਭਾਲਿਆ ਹੈ?",
        "mr": "तुमच्या कुटुंबातील कोणी घटनात्मक पद (उदा. खासदार, आमदार, मंत्री, महापौर) भूषवले आहे का?",
        "te": "మీ కుటుంబ సభ్యులు ఎవరైనా రాజ్యాంగబద్ధమైన పదవిని (ఎంపీ, ఎమ్మెల్యే, మంత్రి) నిర్వహించారా?",
        "ta": "உங்கள் குடும்பத்தில் யாராவது அரசியலமைப்பு பதவி (எம்.பி, எம்.எல்.ஏ, அமைச்சர்) வகித்துள்ளார்களா?",
        "bn": "আপনার পরিবারের কেউ কি কখনো কোনো সাংবিধানিক পদ (যেমন এমপি, বিধায়ক, মন্ত্রী) গ্রহণ করেছেন?",
        "gu": "શું તમારા પરિવારના કોઈ સભ્યએ બંધારણીય પદ (જેમ કે સાંસદ, ધારાસભ્ય, મંત્રી) સંભાળ્યું છે?",
        "kn": "ನಿಮ್ಮ ಕುಟುಂಬದ ಯಾರಾದರೂ ಸಾಂವಿಧಾನಿಕ ಹುದ್ದೆಯನ್ನು (ಸಂಸದ, ಶಾಸಕ, ಸಚಿವರು) ಹೊಂದಿದ್ದಾರೆಯೇ?",
    },
    {
        "field": "is_government_employee",
        "type": "boolean",
        "en": "Are you or anyone in your immediate family currently serving or retired as a government or PSU employee?",
        "hi": "क्या आप या आपके परिवार का कोई सदस्य सरकारी सेवा या पीएसयू (PSU) में कार्यरत या सेवानिवृत्त हैं?",
        "pa": "ਕੀ ਤੁਸੀਂ ਜਾਂ ਤੁਹਾਡਾ ਕੋਈ ਪਰਿਵਾਰਕ ਮੈਂਬਰ ਸਰਕਾਰੀ ਜਾਂ ਪੀਐਸਯੂ ਮੁਲਾਜ਼ਮ ਰਹੇ ਹਨ?",
        "mr": "तुम्ही किंवा तुमच्या कुटुंबातील कोणी सरकारी किंवा निमसरकारी सेवेत कार्यरत किंवा निवृत्त आहात का?",
        "te": "మీరు లేదా మీ కుటుంబ సభ్యులు ఎవరైనా ప్రభుత్వ లేదా పీఎస్‌యూ ఉద్యోగిగా పనిచేశారా?",
        "ta": "நீங்கள் அல்லது உங்கள் குடும்பத்தினர் அரசு அல்லது பொதுத்துறை பணியாளராக உள்ளீர்களா?",
        "bn": "আপনি বা আপনার পরিবারের কেউ কি সরকারি বা রাষ্ট্রায়ত্ত প্রতিষ্ঠানে কর্মরত বা অবসরপ্রাপ্ত?",
        "gu": "શું તમે અથવા તમારા પરિવારના કોઈ સરકારી કે પીએસયુમાં નોકરી કરે છે કે નિવૃત્ત છે?",
        "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದವರು ಸರ್ಕಾರಿ ಅಥವಾ ಸಾರ್ವಜನಿಕ ವಲಯದ ನೌಕರರಾಗಿದ್ದೀರಾ?",
    },
    {
        "field": "is_class_iv_or_group_d",
        "type": "boolean",
        "condition": lambda p: bool(p.get("is_government_employee")) or (p.get("monthly_pension", 0.0) or 0.0) >= 10000.0,
        "default": False,
        "en": "Was that employment in Class IV, Group D, or Multi-Tasking Staff (MTS)?",
        "hi": "क्या वह नौकरी चतुर्थ श्रेणी (Class IV / Group D / MTS) में थी?",
        "pa": "ਕੀ ਉਹ ਨੌਕਰੀ ਚੌਥੀ ਸ਼੍ਰੇਣੀ (Group D / Class IV / MTS) ਵਿੱਚ ਸੀ?",
        "mr": "ती नोकरी वर्ग ४ / गट ड / एमटीएस (Class IV / Group D / MTS) मध्ये होती का?",
        "te": "ఆ ఉద్యోగం క్లాస్ IV / గ్రూప్ డి / ఎంటిఎస్ (Group D) లోదా?",
        "ta": "அந்த வேலை குரூப் டி (Group D / Class IV) பணியிலா?",
        "bn": "সেই চাকরিটি কি গ্রুপ ডি বা চতুর্থ শ্রেণীর (Class IV / Group D) ছিল?",
        "gu": "શું તે નોકરી વર્ગ-૪ / ગ્રુપ ડી (Class IV / Group D) માં હતી?",
        "kn": "ಆ ಉದ್ಯೋಗವು ನಾಲ್ಕನೇ ದರ್ಜೆ / ಗ್ರೂಪ್ ಡಿ (Group D) ನಲ್ಲಿದೆಯೇ?",
    },
    {
        "field": "monthly_pension",
        "type": "float",
        "en": "If receiving a retirement pension, what is the monthly pension amount in Rupees? (Enter 0 if none)",
        "hi": "यदि सेवानिवृत्ति पेंशन मिलती है, तो प्रति माह कितनी पेंशन राशि मिलती है? (यदि नहीं तो 0 दर्ज करें)",
        "pa": "ਜੇਕਰ ਰਿਟਾਇਰਮੈਂਟ ਪੈਨਸ਼ਨ ਮਿਲਦੀ ਹੈ, ਤਾਂ ਪ੍ਰਤੀ ਮਹੀਨਾ ਕਿੰਨੀ ਰਕਮ ਹੈ? (ਨਹੀਂ ਤਾਂ 0 ਦਰਜ ਕਰੋ)",
        "mr": "निवृत्तीवेतन मिळत असल्यास, दरमहा किती पेन्शन मिळते? (नसल्यास ० प्रविष्ट करा)",
        "te": "పింఛను వస్తుంటే, నెలకు ఎంత మొత్తం వస్తుంది? (ఏమీ లేకపోతే 0 నమోదు చేయండి)",
        "ta": "ஓய்வூதியம் பெற்றால், மாத ஓய்வூதியம் எவ்வளவு? (இல்லையெனில் 0 என உள்ளிடவும்)",
        "bn": "পেনশন পেলে, প্রতি মাসে কত টাকা পান? (না পেলে ০ লিখুন)",
        "gu": "પેન્શન મળતું હોય તો માસિક પેન્શનની રકમ કેટલી છે? (ન હોય તો 0 દાખલ કરો)",
        "kn": "ನಿವೃತ್ತಿ ವೇತನ ಪಡೆಯುತ್ತಿದ್ದರೆ, ಮಾಸಿಕ ಪಿಂಚಣಿ ಮೊತ್ತ ಎಷ್ಟು? (ಇಲ್ಲದಿದ್ದರೆ 0 ನಮೂದಿಸಿ)",
    },
    {
        "field": "paid_income_tax_last_ay",
        "type": "boolean",
        "en": "Did you or any member of your farmer family pay Income Tax in the last assessment year?",
        "hi": "क्या आपने या आपके परिवार के किसी सदस्य ने पिछले आकलन वर्ष में आयकर (Income Tax) का भुगतान किया था?",
        "pa": "ਕੀ ਤੁਸੀਂ ਜਾਂ ਤੁਹਾਡੇ ਪਰਿਵਾਰ ਦੇ ਕਿਸੇ ਮੈਂਬਰ ਨੇ ਪਿਛਲੇ ਸਾਲ ਇਨਕਮ ਟੈਕਸ ਭਰਿਆ ਸੀ?",
        "mr": "तुम्ही किंवा तुमच्या कुटुंबातील कोणी मागील वर्षात आयकर (Income Tax) भरला होता का?",
        "te": "మీరు లేదా మీ కుటుంబ సభ్యులు గత ఆర్థిక సంవత్సరంలో ఆదాయపు పన్ను (Income Tax) చెల్లించారా?",
        "ta": "நீங்களோ உங்கள் குடும்பத்தினரோ கடந்த ஆண்டில் வருமான வரி (Income Tax) செலுத்தியுள்ளீர்களா?",
        "bn": "আপনি বা আপনার পরিবারের কেউ কি গত মূল্যায়ন বছরে আয়কর প্রদান করেছেন?",
        "gu": "શું તમે અથવા તમારા પરિવારે છેલ્લા આકારણી વર્ષમાં આવકવેરો ભર્યો હતો?",
        "kn": "ನೀವು ಅಥವಾ ನಿಮ್ಮ ಕುಟುಂಬದವರು ಕಳೆದ ವರ್ಷದಲ್ಲಿ ಆದಾಯ ತೆರಿಗೆ (Income Tax) ಪಾವತಿಸಿದ್ದೀರಾ?",
    },
    {
        "field": "is_registered_professional",
        "type": "boolean",
        "en": "Are you a practicing Doctor, Lawyer, Chartered Accountant, or Engineer registered with a professional body?",
        "hi": "क्या आप डॉक्टर, वकील, चार्टर्ड अकाउंटेंट (CA) या इंजीनियर के रूप में पंजीकृत और कार्यरत हैं?",
        "pa": "ਕੀ ਤੁਸੀਂ ਡਾਕਟਰ, ਵਕੀਲ, ਚਾਰਟਰਡ ਅਕਾਊਂਟੈਂਟ (CA) ਜਾਂ ਇੰਜੀਨੀਅਰ ਵਜੋਂ ਰਜਿਸਟਰਡ ਹੋ?",
        "mr": "तुम्ही डॉक्टर, वकील, चार्टर्ड अकाउंटंट (CA) किंवा अभियंता म्हणून नोंदणीकृत व्यावसायिक आहात का?",
        "te": "మీరు డాక్టర్, లాయర్, చార్టర్డ్ అకౌంటెంట్ (CA) లేదా ఇంజనీర్‌గా ప్రాక్టీస్ చేస్తున్నారా?",
        "ta": "நீங்கள் பதிவுசெய்த மருத்துவர், வழக்கறிஞர், ஆடிட்டர் (CA) அல்லது பொறியாளரா?",
        "bn": "আপনি কি কোনো ডাক্তার, উকিল, চার্টার্ড অ্যাকাউন্ট্যান্ট (CA) বা ইঞ্জিনিয়ার হিসেবে নিবন্ধিত?",
        "gu": "શું તમે ડોક્ટર, વકીલ, સીએ (CA) અથવા એન્જિનિયર તરીકે નોંધાયેલા વ્યાવસાયિક છો?",
        "kn": "ನೀವು ವೈದ್ಯರು, ವಕೀಲರು, ಚಾರ್ಟರ್ಡ್ ಅಕೌಂಟೆಂಟ್ (CA) ಅಥವಾ ಎಂಜಿನಿಯರ್ ಆಗಿ ನೋಂದಾಯಿಸಿಕೊಂಡಿದ್ದೀರಾ?",
    },
]


class InterviewEngine:
    """Interviews citizen to populate profile fields for the deterministic rules engine.
    The LLM never determines or states eligibility itself.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()

    def _extract_value_deterministic(self, field_def: Dict[str, Any], user_msg: str) -> Any:
        """Deterministic fallback value extractor supporting English and 8 major Indic languages."""
        msg = user_msg.strip().lower()
        f_type = field_def.get("type", "string")

        if f_type == "boolean":
            # Match affirmative across English and Indic languages
            affirmative_tokens = [
                "yes", "yeah", "yup", "ha", "haan", "sahi", "true", "1", "sure", "definitely", "done", "completed", "already", "hai",
                "हाँ", "हां", "हा", "बिल्कुल", "सही", "अवश्य", "हो गया", "कर लिया",
                "ਹਾਂ", "ਹਾਂਜੀ", "ਸਹੀ", "ਹੋ ਗਿਆ",
                "होय", "हो", "आहे",
                "అవును", "అవునండి", "సరే",
                "ஆம்", "ஆமாம்", "சரி",
                "হ্যাঁ", "হাঁ", "আছে",
                "હા", "હાજી", "સાચું",
                "ಹೌದು", "ಸರಿ", "ಇದೆ",
            ]
            if re.search(r"\b(yes|yeah|yup|ha|haan|sahi|true|1|sure|definitely|done|completed|already|hai|h)\b", msg) or any(
                token in msg for token in affirmative_tokens
            ):
                return True

            # Match negative across English and Indic languages
            negative_tokens = [
                "no", "nope", "nah", "nahi", "nahin", "false", "0", "not", "never", "pending",
                "नहीं", "ना", "नाही", "गलत", "बाकी है", "लंबित",
                "ਨਹੀਂ", "ਨਾ",
                "नाही", "ना",
                "కాదు", "లేదు",
                "இல்லை", "இல்ல",
                "না", "নেই",
                "ના", "નથી",
                "ಇಲ್ಲ", "ಬೇಡ",
            ]
            if re.search(r"\b(no|nope|nah|nahi|nahin|false|0|not|never|pending)\b", msg) or any(
                token in msg for token in negative_tokens
            ):
                return False

            return True if "yes" in msg or "ha" in msg else False

        elif f_type == "float":
            # Find numbers
            numbers = re.findall(r"(\d+(?:\.\d+)?)", msg)
            if numbers:
                val = float(numbers[0])
                if any(w in msg for w in ["acre", "एकड़", "ਏਕੜ", "एकर", "ఎకరం", "ஏக்கர்", "একর"]):
                    val = round(val * 0.4047, 2)
                return val
            return 0.0

        return msg

    def extract_field_value(self, field_name: str, user_msg: str) -> Any:
        """Extracts structured value using Gemini (if live) or deterministic extractor."""
        field_def = next((f for f in FIELD_QUESTIONS if f["field"] == field_name), None)
        if not field_def:
            return user_msg

        if self.gemini.is_live:
            f_type = field_def.get("type", "string")
            prompt = (
                f"Extract the citizen's response for field '{field_name}' (expected type: {f_type}).\n"
                f"Question asked: {field_def.get('en')}\n"
                f"Citizen response: '{user_msg}'\n\n"
                f"Output strictly a JSON object with a single key 'value' containing the parsed value."
            )
            try:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"},
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{self.gemini.generate_url}?key={self.gemini.api_key}",
                        json=payload,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text_part = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(text_part)
                        if "value" in parsed:
                            return parsed["value"]
            except Exception:
                pass

        return self._extract_value_deterministic(field_def, user_msg)

    def get_next_missing_field(self, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Finds the next required field not yet filled in profile."""
        for f in FIELD_QUESTIONS:
            cond = f.get("condition")
            if cond and not cond(profile):
                continue
            if f["field"] not in profile or profile[f["field"]] is None:
                return f
        return None

    def process_turn(
        self,
        user_message: str,
        profile: Dict[str, Any],
        current_field: Optional[str] = None,
        lang: str = "en",
    ) -> Dict[str, Any]:
        """Runs one conversational turn."""
        updated_profile = dict(profile)

        # 1. If replying to a current field, extract its value
        if current_field and user_message.strip():
            extracted = self.extract_field_value(current_field, user_message)
            updated_profile[current_field] = extracted

        # 2. Determine next field to ask
        next_field_def = self.get_next_missing_field(updated_profile)

        # Calculate remaining missing fields
        missing_fields = []
        for f in FIELD_QUESTIONS:
            cond = f.get("condition")
            if cond and not cond(updated_profile):
                continue
            if f["field"] not in updated_profile or updated_profile[f["field"]] is None:
                missing_fields.append(f["field"])

        # 3. If all fields are collected -> invoke rule engine (LLM NEVER states eligibility)
        if not next_field_def:
            if "family_member_paid_income_tax" not in updated_profile:
                updated_profile["family_member_paid_income_tax"] = updated_profile.get("paid_income_tax_last_ay", False)

            verdict_result = evaluate_profile(updated_profile)
            complete_messages = {
                "en": "All intake details have been collected. Evaluating your profile against the official PM-KISAN eligibility rules engine...",
                "hi": "सभी आवश्यक विवरण एकत्र कर लिए गए हैं। आधिकारिक नियम इंजन द्वारा आपके विवरण की जांच की जा रही है...",
                "pa": "ਸਾਰੇ ਜ਼ਰੂਰੀ ਵੇਰਵੇ ਇਕੱਠੇ ਕਰ ਲਏ ਗਏ ਹਨ। ਅਧਿਕਾਰਤ ਨਿਯਮ ਇੰਜਣ ਦੁਆਰਾ ਤੁਹਾਡੀ ਪਾਤਰਤਾ ਦੀ ਜਾਂਚ ਕੀਤੀ ਜਾ ਰਹੀ ਹੈ...",
                "mr": "सर्व आवश्यक माहिती गोळा करण्यात आली आहे. अधिकृत नियम इंजिनद्वारे तुमच्या पात्रतेचे मूल्यांकन केले जात आहे...",
                "te": "అన్ని వివరాలు సేకరించబడ్డాయి. అధికారిక నిబంధనల ఇంజిన్ ద్వారా మీ అర్హత పరిశీలించబడుతోంది...",
                "ta": "அனைத்து விவரங்களும் சேகரிக்கப்பட்டன. அதிகாரப்பூர்வ விதிகளின்படி உங்கள் தகுதி சரிபார்க்கப்படுகிறது...",
                "bn": "সমস্ত প্রয়োজনীয় তথ্য সংগ্রহ করা হয়েছে। আনুষ্ঠানিক নিয়ম ইঞ্জিন দ্বারা আপনার যোগ্যতা যাচাই করা হচ্ছে...",
                "gu": "બધી જરૂરી વિગતો એકત્રિત કરવામાં આવી છે. સત્તાવાર નિયમ એન્જિન દ્વારા તમારી પાત્રતાની ચકાસણી થઈ રહી છે...",
                "kn": "ಎಲ್ಲಾ ಅಗತ್ಯ ವಿವರಗಳನ್ನು ಸಂಗ್ರಹಿಸಲಾಗಿದೆ. ಅಧಿಕೃತ ನಿಯಮಗಳ ಎಂಜಿನ್ ಮೂಲಕ ನಿಮ್ಮ ಅರ್ಹತೆಯನ್ನು ಮೌಲ್ಯಮಾಪನ ಮಾಡಲಾಗುತ್ತಿದೆ...",
            }
            complete_msg = complete_messages.get(lang, complete_messages["en"])

            return {
                "assistant_message": complete_msg,
                "current_field": None,
                "extracted_profile": updated_profile,
                "missing_fields": [],
                "is_complete": True,
                "verdict_result": verdict_result,
            }

        # 4. Generate next question in user's language
        next_field_name = next_field_def["field"]
        q_text = next_field_def.get(lang, next_field_def.get("en", ""))

        return {
            "assistant_message": q_text,
            "current_field": next_field_name,
            "extracted_profile": updated_profile,
            "missing_fields": missing_fields,
            "is_complete": False,
            "verdict_result": None,
        }


# Singleton instance
_interview_engine: Optional[InterviewEngine] = None


def get_interview_engine() -> InterviewEngine:
    global _interview_engine
    if _interview_engine is None:
        _interview_engine = InterviewEngine()
    return _interview_engine
