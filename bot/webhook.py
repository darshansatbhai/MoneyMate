import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from bot import get_application

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

application = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global application
    application = get_application()
    if not application:
        logger.error("Failed to initialize Telegram application.")
        yield
        return
        
    await application.initialize()
    await application.start()
    
    webhook_url = os.getenv("WEBHOOK_URL")
    secret_token = os.getenv("WEBHOOK_SECRET", "super_secret_token_123")
    
    if webhook_url:
        await application.bot.set_webhook(url=webhook_url, secret_token=secret_token)
        logger.info(f"Webhook set to {webhook_url}")
    else:
        logger.info("WEBHOOK_URL not set! Running in background polling mode with active HTTP health check...")
        await application.bot.delete_webhook(drop_pending_updates=False)
        await application.updater.start_polling()
        
    yield
    
    if application:
        if application.updater and application.updater.running:
            await application.updater.stop()
        await application.stop()
        await application.shutdown()


app = FastAPI(lifespan=lifespan)

@app.post("/telegram")
async def telegram_webhook(request: Request):
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    expected_secret = os.getenv("WEBHOOK_SECRET", "super_secret_token_123")
    
    if secret_token != expected_secret:
        return Response(status_code=403, content="Forbidden")
        
    data = await request.json()
    update = Update.de_json(data, application.bot)
    
    await application.process_update(update)
    return Response(status_code=200, content="OK")

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "MoneyMate Bot is running"}
