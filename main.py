import os
import threading
import json
import logging
from flask import Flask, jsonify
from telegram import Update, Bot
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext
)
from auth_helper import AuthInstance
from my_package import fetch_my_packages
from paket_xut import get_package_xut
from paket_custom_family import get_packages_by_family
from api_request import get_balance, get_otp, submit_otp

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variabel Lingkungan
BOT_TOKEN = "8319444433:AAHRLxXy4hqGnXsVLR_vSwCIsnSirX_vwcE"
BASE_API_URL = "https://api.myxl.xlaxiata.co.id"
BASE_CIAM_URL = "https://gede.ciam.xlaxiata.co.id"
BASIC_AUTH = "OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z"
AX_DEVICE_ID = "92fb44c0804233eb4d9e29f838223a14"
AX_FP_KEY = "18b4d589826af50241177961590e6693"
UA = "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13"
API_KEY = "vT8tINqHaOxXbGE7eOWAhA=="
AES_KEY_ASCII = "5dccbf08920a5527"

# Inisialisasi AuthInstance
AuthInstance.api_key = API_KEY
AuthInstance.aes_key_ascii = AES_KEY_ASCII

# Inisialisasi Flask
app = Flask(__name__)

# --- Flask Routes ---
@app.route('/')
def index():
    return jsonify({"message": "Bot is running! by @MzCoder"})

# --- Command Handlers ---
def start(update: Update, context: CallbackContext) -> None:
    """Mengirim pesan sambutan."""
    update.message.reply_text('Halo! Saya bot manajemen akun. Gunakan /gantiakun untuk memulai atau /menu untuk melihat opsi.')

def menu(update: Update, context: CallbackContext) -> None:
    """Menampilkan informasi akun dan saldo."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Anda belum login. Silakan gunakan /gantiakun.")
        return

    try:
        balance = get_balance(AuthInstance.api_key, active_user["tokens"]["id_token"])
        balance_remaining = balance.get("remaining")
        balance_expired_at = balance.get("expired_at")

        message = (
            f"👤 **Akun Saya**\n"
            f"--------------------------\n"
            f"• **Nomor**: `{active_user['number']}`\n"
            f"• **Sisa Saldo**: Rp {balance_remaining}\n"
            f"• **Berlaku Hingga**: {balance_expired_at}"
        )
        update.message.reply_markdown_v2(message, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        update.message.reply_text("Gagal mengambil info akun. Token mungkin kedaluwarsa. Mohon coba login ulang.")

def cekpaket(update: Update, context: CallbackContext) -> None:
    """Menampilkan paket yang terdaftar."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Anda belum login. Silakan gunakan /gantiakun.")
        return

    try:
        packages = fetch_my_packages(active_user["tokens"]["id_token"])
        if packages:
            message = "📦 **Paket Saya**\n"
            message += "--------------------------\n"
            for pkg in packages:
                message += f"• **Nama**: {pkg.get('name')}\n"
                message += f"• **Kode Kuota**: `{pkg.get('quota_code')}`\n"
                message += f"• **Kode Keluarga**: `{pkg.get('family_code')}`\n"
                message += "--------------------------\n"
            update.message.reply_markdown_v2(message, disable_web_page_preview=True)
        else:
            update.message.reply_text("Tidak ada paket yang ditemukan.")
    except Exception as e:
        logger.error(f"Error fetching my packages: {e}")
        update.message.reply_text("Gagal mengambil data paket. Mohon coba lagi.")

def xut(update: Update, context: CallbackContext) -> None:
    """Menampilkan paket XUT."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Anda belum login. Silakan gunakan /gantiakun.")
        return
    
    try:
        packages = get_package_xut()
        if packages:
            message = "🎁 **Paket XUT**\n"
            message += "--------------------------\n"
            for pkg in packages:
                message += f"• **Nama**: {pkg['name']} - Rp {pkg['price']}\n"
                message += f"• **Kode**: `{pkg['code']}`\n"
                message += "--------------------------\n"
            update.message.reply_markdown_v2(message, disable_web_page_preview=True)
        else:
            update.message.reply_text("Gagal mengambil paket XUT.")
    except Exception as e:
        logger.error(f"Error fetching XUT packages: {e}")
        update.message.reply_text("Terjadi kesalahan saat mengambil data paket XUT. Silakan coba lagi.")


def family(update: Update, context: CallbackContext) -> None:
    """Meminta Family Code untuk mencari paket kustom."""
    update.message.reply_text("Silakan masukkan Family Code:")
    context.user_data['state'] = 'awaiting_family_code'

def gantiakun(update: Update, context: CallbackContext) -> None:
    """Meminta nomor telepon untuk login."""
    update.message.reply_text("Silakan kirimkan nomor telepon Anda (diawali 628):")
    context.user_data['state'] = 'awaiting_number'

def handle_text(update: Update, context: CallbackContext) -> None:
    """Menangani pesan teks non-perintah."""
    state = context.user_data.get('state')
    text = update.message.text.strip()
    
    if state == 'awaiting_number':
        get_number(update, context)
    elif state == 'awaiting_otp':
        get_otp_code(update, context)
    elif state == 'awaiting_family_code':
        package_custom_fetch(update, context)
    else:
        update.message.reply_text("Maaf, saya tidak mengerti. Silakan gunakan perintah yang ada.")

def get_number(update: Update, context: CallbackContext) -> None:
    contact_number = update.message.text.strip()
    if not contact_number.startswith("628") or not contact_number[1:].isdigit():
        update.message.reply_text("Nomor tidak valid. Mohon pastikan diawali dengan 628.")
        return

    context.user_data['contact_number'] = contact_number
    try:
        subscriber_id = get_otp(contact_number)
        if subscriber_id:
            context.user_data['subscriber_id'] = subscriber_id
            context.user_data['state'] = 'awaiting_otp'
            update.message.reply_text(f"OTP telah dikirim ke nomor {contact_number}. Silakan masukkan kode OTP:")
        else:
            update.message.reply_text("Gagal meminta OTP. Silakan coba lagi nanti.")
            context.user_data['state'] = None
    except Exception as e:
        logger.error(f"Error requesting OTP: {e}")
        update.message.reply_text("Terjadi kesalahan saat meminta OTP.")
        context.user_data['state'] = None

def get_otp_code(update: Update, context: CallbackContext) -> None:
    otp_code = update.message.text.strip()
    contact_number = context.user_data.get('contact_number')
    
    if not contact_number:
        update.message.reply_text("Sesi login berakhir. Mohon mulai lagi dengan /gantiakun.")
        context.user_data['state'] = None
        return

    if not otp_code or len(otp_code) != 6:
        update.message.reply_text("Kode OTP tidak valid. Mohon coba lagi.")
        return

    try:
        tokens = submit_otp(AuthInstance.api_key, contact_number, otp_code)
        if tokens:
            AuthInstance.add_refresh_token(contact_number, tokens["refresh_token"])
            AuthInstance.set_active_user(contact_number)
            update.message.reply_text("Login berhasil! 🎉")
        else:
            update.message.reply_text("Login gagal. Kode OTP mungkin salah.")
    except Exception as e:
        logger.error(f"Error submitting OTP: {e}")
        update.message.reply_text("Terjadi kesalahan saat login.")
    finally:
        context.user_data['state'] = None

def package_custom_fetch(update: Update, context: CallbackContext) -> None:
    family_code = update.message.text.strip()
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Anda belum login. Silakan gunakan /gantiakun.")
        context.user_data['state'] = None
        return

    try:
        packages = get_packages_by_family(family_code)
        if packages:
            message = f"🎁 **Paket Family: {packages[0]['name'].split('-')[0].strip()}**\n"
            message += "--------------------------\n"
            for pkg in packages:
                message += f"• **Nama**: {pkg['name']} - Rp {pkg['price']}\n"
                message += f"• **Kode**: `{pkg['code']}`\n"
                message += "--------------------------\n"
            update.message.reply_markdown_v2(message, disable_web_page_preview=True)
        else:
            update.message.reply_text("Tidak ada paket yang ditemukan untuk Family Code tersebut.")
    except Exception as e:
        logger.error(f"Error fetching custom packages: {e}")
        update.message.reply_text("Terjadi kesalahan saat mengambil paket kustom. Silakan coba lagi.")
    finally:
        context.user_data['state'] = None


# --- Fungsi untuk menjalankan Flask ---
def run_flask():
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)

def main():
    """Jalankan bot dan server Flask di thread terpisah."""

    # Siapkan bot Telegram
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Daftarkan handler
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", menu))
    dispatcher.add_handler(CommandHandler("cekpaket", cekpaket))
    dispatcher.add_handler(CommandHandler("xut", xut))
    dispatcher.add_handler(CommandHandler("family", family))
    dispatcher.add_handler(CommandHandler("gantiakun", gantiakun))

    # Handler pesan teks (non-perintah)
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_text))

    # Mulai bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    # Mulai Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Mulai bot di main thread
    main()
