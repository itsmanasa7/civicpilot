import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.telegram_bot import get_telegram_bot


@pytest.fixture
def bot():
    return get_telegram_bot()


def test_telegram_bot_initialization(bot):
    """Test bot instance initialization and application setup."""
    app = bot.build_application()
    assert app is not None
    assert len(app.handlers) > 0


def test_bot_start_command(bot):
    """Test /start command reply."""
    async def _test():
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        await bot.start_command(update, context)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        assert "Namaste" in args[0]
        assert "PM-KISAN" in args[0]

    asyncio.run(_test())


def test_bot_status_command(bot):
    """Test /status command lookup for Ram Prasad Sharma."""
    async def _test():
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["ram"]
        await bot.status_command(update, context)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        assert "Ram Prasad Sharma" in args[0]
        assert "ELIGIBLE" in args[0]

    asyncio.run(_test())


def test_bot_direct_nudge_dispatch(bot):
    """Test direct citizen nudge dispatch and record keeping."""
    res = bot.send_direct_nudge(
        chat_id="1004",
        message="Urgent: Rule change PMK-A-1.3 applied.",
        nudge_type="RULE_CHANGED",
    )
    assert res["delivered"] is True
    assert res["chat_id"] == "1004"
    assert len(bot.sent_messages) > 0
