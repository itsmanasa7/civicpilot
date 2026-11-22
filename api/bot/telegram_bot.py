import asyncio
import io
import os
import sys
from typing import Any, Dict, List, Optional
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from demo_users import SEEDED_DEMO_USERS, get_demo_users
from rag.service import RAGService
from voice.service import get_voice_service
from rules.simulator import get_rule_simulator


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


class CivicPilotTelegramBot:
    """CivicPilot PM-KISAN Telegram Bot with proactive nudges & voice note intelligence."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.rag = RAGService()
        self.voice = get_voice_service()
        self.simulator = get_rule_simulator()
        self.application: Optional[Application] = None
        self.sent_messages: List[Dict[str, Any]] = []

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command."""
        welcome_text = (
            "🏛️ *Namaste! Welcome to CivicPilot PM-KISAN Assistant.*\n\n"
            "I provide grounded assistance for the PM-KISAN Samman Nidhi scheme:\n"
            "• 🎙️ *Voice Notes:* Send me any voice message in English or Hindi.\n"
            "• 📊 */status:* Check your beneficiary eligibility and pending actions.\n"
            "• 🔔 */nudges:* View proactive alerts (deadlines, missing records, rule changes).\n"
            "• ❓ *Q&A:* Ask any question about scheme clauses and guidelines."
        )
        if update.message:
            await update.message.reply_text(welcome_text, parse_mode="Markdown")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /status command."""
        args = context.args if context else []
        query = args[0].lower() if args else "ram"

        # Search in seeded demo users
        matched = None
        for u in SEEDED_DEMO_USERS:
            if query in u["name"].lower() or query in u["mobile"]:
                matched = u
                break
        if not matched:
            matched = SEEDED_DEMO_USERS[0]

        name = matched["name"]
        status = matched["initial_status"]
        pending = matched.get("pending_items", [])
        pending_str = (
            "\n".join([f"• {p}" for p in pending]) if pending else "• All documents verified."
        )

        resp = (
            f"📋 *PM-KISAN Status for {name}:*\n"
            f"• *Current Verdict:* {status}\n"
            f"• *Landholding:* {matched['land_area_ha']} Ha (Plot: {matched['khasra_no']})\n"
            f"• *District:* {matched['district']}, {matched['state']}\n\n"
            f"*Action Items / Pending Requirements:*\n{pending_str}"
        )
        if update.message:
            await update.message.reply_text(resp, parse_mode="Markdown")

    async def nudges_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /nudges command to simulate proactive citizen reminders."""
        nudges = self.simulator.run_cron_nudge_dispatch()
        if not nudges:
            text = "✅ No urgent alerts pending at this time."
        else:
            text = "🔔 *Proactive Citizen Nudges Dispatched:*\n\n"
            for n in nudges[:3]:
                text += f"*{n['nudge_type']}* (Clause [{n.get('clause_cited', 'PM-KISAN')}])\n{n['message']}\n\n"

        if update.message:
            await update.message.reply_text(text, parse_mode="Markdown")

    async def handle_voice_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes incoming voice notes using Gemini speech-to-text + RAG grounded Q&A."""
        if not update.message or not update.message.voice:
            return

        # Let user know voice note is being processed
        status_msg = await update.message.reply_text("🎧 Transcribing audio with Gemini Speech AI...")

        try:
            # Download voice note file
            voice_file = await update.message.voice.get_file()
            audio_stream = io.BytesIO()
            await voice_file.download_to_memory(out=audio_stream)
            audio_bytes = audio_stream.getvalue()

            # Transcribe audio using VoiceService
            transcription_res = self.voice.transcribe(
                audio_bytes, mime_type="audio/ogg", lang="en"
            )
            transcribed_text = transcription_res.get("text", "")

            await status_msg.edit_text(f"🗣️ *Transcribed Speech:*\n_{transcribed_text}_\n\n🔍 Querying PM-KISAN Scheme Guidelines...", parse_mode="Markdown")

            # Run through RAG scheme assistant
            rag_res = self.rag.ask(transcribed_text, lang=transcription_res.get("lang", "en"))
            citations_str = ""
            if rag_res.citations:
                c_ids = ", ".join([f"[{c.id}]" for c in rag_res.citations])
                citations_str = f"\n\n📜 *Official Citations:* {c_ids}"

            final_reply = (
                f"🗣️ *You Asked:* \"{transcribed_text}\"\n\n"
                f"🏛️ *CivicPilot Guidance:*\n{rag_res.answer}"
                f"{citations_str}"
            )
            await status_msg.edit_text(final_reply, parse_mode="Markdown")

        except Exception as e:
            await status_msg.edit_text(f"⚠️ Error processing voice message: {str(e)}")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes incoming citizen text questions."""
        if not update.message or not update.message.text:
            return

        question = update.message.text.strip()
        rag_res = self.rag.ask(question)
        citations_str = ""
        if rag_res.citations:
            c_ids = ", ".join([f"[{c.id}]" for c in rag_res.citations])
            citations_str = f"\n\n📜 *Citations:* {c_ids}"

        reply = f"🏛️ *CivicPilot Scheme Assistant:*\n{rag_res.answer}{citations_str}"
        await update.message.reply_text(reply, parse_mode="Markdown")

    def build_application(self) -> Application:
        """Constructs the Telegram bot Application with all registered handlers."""
        app = ApplicationBuilder().token(self.token or "123456:FAKE_TOKEN_FOR_SIMULATION").build()
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("nudges", self.nudges_command))
        app.add_handler(MessageHandler(filters.VOICE, self.handle_voice_note))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_text_message))
        self.application = app
        return app

    def send_direct_nudge(self, chat_id: str, message: str, nudge_type: str = "NUDGE") -> Dict[str, Any]:
        """Sends or records a direct nudge notification for a citizen."""
        record = {
            "chat_id": chat_id,
            "message": message,
            "nudge_type": nudge_type,
            "delivered": True,
        }
        self.sent_messages.append(record)
        return record


# Singleton instance
_telegram_bot: Optional[CivicPilotTelegramBot] = None


def get_telegram_bot() -> CivicPilotTelegramBot:
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = CivicPilotTelegramBot()
    return _telegram_bot


if __name__ == "__main__":
    bot = get_telegram_bot()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[Telegram Bot] No TELEGRAM_BOT_TOKEN specified in environment. Simulation mode ready.")
        sys.exit(0)
    print("[Telegram Bot] Starting polling with active bot token...")
    app = bot.build_application()
    app.run_polling()
