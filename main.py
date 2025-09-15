import sys
import os
import json
import threading
import logging
from flask import Flask, jsonify, request
from telegram import Update, Bot
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)

from auth_helper import AuthInstance
from my_package import fetch_my_packages
from paket_xut import get_package_xut
from paket_custom_family import get_packages_by_family
from api_request import get_balance, get_otp, submit_otp, BASE_API_URL, BASE_CIAM_URL, BASIC_AUTH, AX_DEVICE_ID, AX_FP, UA

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variabel Lingkungan
BOT_TOKEN = "8319444433:AAHRLxXy4hqGnXsVLR_vSwCIsnSirX_vwcE"
API_KEY = "ed17ec92-a8e4-42d0-a635-4c62a982ed0a"

# Auth Instance
AuthInstance.api_key = API_KEY

# States untuk ConversationHandler
NUMBER, OTP, FAMILY_CODE = range(3)

# Command Handlers
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
        packages = fetch_my_packages()
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


def gantiakun(update: Update, context: CallbackContext) -> int:
    """Memulai alur login dengan meminta nomor telepon."""
    update.message.reply_text("Silakan kirimkan nomor telepon Anda (diawali 628):")
    return NUMBER

def get_number(update: Update, context: CallbackContext) -> int:
    """Menangani nomor telepon dan meminta OTP."""
    contact_number = update.message.text.strip()
    if not contact_number.startswith("628") or not contact_number[1:].isdigit():
        update.message.reply_text("Nomor tidak valid. Mohon pastikan diawali dengan 628.")
        return NUMBER

    context.user_data['contact_number'] = contact_number
    try:
        subscriber_id = get_otp(contact_number)
        if subscriber_id:
            context.user_data['subscriber_id'] = subscriber_id
            update.message.reply_text(f"OTP telah dikirim ke nomor {contact_number}. Silakan masukkan kode OTP:")
            return OTP
        else:
            update.message.reply_text("Gagal meminta OTP. Silakan coba lagi nanti.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error requesting OTP: {e}")
        update.message.reply_text("Terjadi kesalahan saat meminta OTP.")
        return ConversationHandler.END

def get_otp_code(update: Update, context: CallbackContext) -> int:
    """Menangani kode OTP dan mengajukannya untuk mendapatkan token."""
    otp_code = update.message.text.strip()
    contact_number = context.user_data.get('contact_number')
    if not contact_number:
        update.message.reply_text("Sesi login berakhir. Mohon mulai lagi dengan /gantiakun.")
        return ConversationHandler.END

    if not otp_code or len(otp_code) != 6:
        update.message.reply_text("Kode OTP tidak valid. Mohon coba lagi.")
        return OTP

    try:
        tokens = submit_otp(AuthInstance.api_key, contact_number, otp_code)
        if tokens:
            AuthInstance.add_refresh_token(contact_number, tokens["refresh_token"])
            AuthInstance.set_active_user(contact_number)
            update.message.reply_text("Login berhasil! 🎉")
            return ConversationHandler.END
        else:
            update.message.reply_text("Login gagal. Kode OTP mungkin salah.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error submitting OTP: {e}")
        update.message.reply_text("Terjadi kesalahan saat login. Silakan coba lagi nanti.")
        return ConversationHandler.END

def family(update: Update, context: CallbackContext) -> int:
    """Meminta Family Code untuk mencari paket kustom."""
    update.message.reply_text("Silakan masukkan Family Code:")
    return FAMILY_CODE

def package_custom_fetch(update: Update, context: CallbackContext) -> int:
    """Mengambil paket kustom berdasarkan Family Code."""
    family_code = update.message.text.strip()
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Anda belum login. Silakan gunakan /gantiakun.")
        return ConversationHandler.END

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
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Membatalkan alur percakapan."""
    update.message.reply_text("Proses dibatalkan.")
    return ConversationHandler.END

def main():
    """Jalankan bot Telegram."""
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Handler untuk ganti akun (login)
    login_handler = ConversationHandler(
        entry_points=[CommandHandler('gantiakun', gantiakun)],
        states={
            NUMBER: [MessageHandler(Filters.text & ~Filters.command, get_number)],
            OTP: [MessageHandler(Filters.text & ~Filters.command, get_otp_code)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(login_handler)
    
    # Handler untuk paket kustom
    custom_package_handler = ConversationHandler(
        entry_points=[CommandHandler('family', family)],
        states={
            FAMILY_CODE: [MessageHandler(Filters.text & ~Filters.command, package_custom_fetch)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(custom_package_handler)

    # Handler untuk perintah lainnya
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", menu))
    dispatcher.add_handler(CommandHandler("cekpaket", cekpaket))
    dispatcher.add_handler(CommandHandler("xut", xut))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting the application.")
    except Exception as e:
        print(f"An error occurred: {e}")
