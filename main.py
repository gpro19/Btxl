import os
import threading
import logging
from flask import Flask, jsonify

# Impor kelas yang diperlukan untuk python-telegram-bot versi 13.7
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)

# Impor semua fungsi dari file Anda yang sudah ada
from auth_helper import AuthInstance, get_otp_and_handle_session, submit_otp_and_login_session
from my_package import get_my_packages_data
from paket_xut import get_package_xut
from paket_custom_family import get_packages_by_family
from api_request import get_balance
from purchase_api import settlement_multipayment

# Aktifkan logging untuk melacak bot
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Ambil token bot dari variabel lingkungan untuk keamanan
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8319444433:AAHRLxXy4hqGnXsVLR_vSwCIsnSirX_vwcE")

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# --- Handler untuk Perintah Telegram ---
def start(update: Update, context: CallbackContext) -> None:
    """Mengirim pesan sambutan saat perintah /start diberikan."""
    update.message.reply_text(
        "Selamat datang! Kirim nomor XL Anda (diawali 628) untuk login, atau gunakan /menu untuk melihat opsi."
    )

def menu(update: Update, context: CallbackContext) -> None:
    """Menampilkan menu utama dan saldo pengguna."""
    active_user = AuthInstance.get_active_user()

    if active_user:
        balance = get_balance(AuthInstance.api_key, active_user["tokens"]["id_token"])
        balance_text = f"Saldo Anda: Rp {balance.get('remaining', 'N/A')}\n"
        menu_text = (
            "Pilih opsi:\n"
            "/cekpaket - Cek paket saya\n"
            "/xut - Beli paket Unli Turbo\n"
            "/family - Beli paket Family\n"
            "/gantiakun - Ganti akun/logout"
        )
        update.message.reply_text(f"{balance_text}\n{menu_text}")
    else:
        update.message.reply_text("Anda belum login. Silakan kirim nomor XL Anda untuk login.")

def cekpaket(update: Update, context: CallbackContext) -> None:
    """Mengambil dan menampilkan paket yang dimiliki pengguna."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Silakan login terlebih dahulu.")
        return

    update.message.reply_text("Memuat paket Anda, mohon tunggu...")
    packages = get_my_packages_data()

    if packages:
        text = "Paket Anda:\n\n"
        for i, pkg in enumerate(packages):
            text += f"{i+1}. {pkg['name']} (Quota: {pkg['remaining_quota']})\n"
        update.message.reply_text(text)
    else:
        update.message.reply_text("Gagal mengambil paket. Silakan coba lagi.")


def xut(update: Update, context: CallbackContext) -> None:
    """Menampilkan daftar paket XUT."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        update.message.reply_text("Silakan login terlebih dahulu.")
        return

    packages = get_package_xut()
    if packages:
        text = "Paket Unli Turbo (XUT):\n\n"
        for pkg in packages:
            text += f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}\n"
        update.message.reply_text(text)
        update.message.reply_text("Pilih paket dengan mengirimkan nomornya. Contoh: `1`")

        # Simpan paket di context untuk diproses di langkah berikutnya
        context.user_data['xut_packages'] = {p['number']: p for p in packages}
        context.user_data['state'] = 'awaiting_xut_choice'

    else:
        update.message.reply_text("Gagal mengambil paket XUT.")

def family(update: Update, context: CallbackContext) -> None:
    """Meminta kode family dari pengguna."""
    update.message.reply_text("Silakan kirim kode family yang ingin Anda lihat paketnya.")
    context.user_data['state'] = 'awaiting_family_code'

def gantiakun(update: Update, context: CallbackContext) -> None:
    """Menghapus pengguna aktif dan memulai ulang proses login."""
    AuthInstance.set_active_user(None)
    update.message.reply_text("Akun berhasil diganti. Silakan kirim nomor baru untuk login.")

# --- Handler untuk Pesan Teks ---
def handle_text(update: Update, context: CallbackContext) -> None:
    """Menangani pesan teks apa pun, termasuk alur login dan pembelian."""
    text = update.message.text
    user_id = update.effective_user.id
    current_state = context.user_data.get('state')

    if current_state == 'awaiting_otp':
        phone_number = context.user_data.get('phone_number')
        if submit_otp_and_login_session(user_id, phone_number, text):
            update.message.reply_text("Login berhasil! Gunakan /menu untuk melihat opsi.")
            context.user_data.clear() # Hapus state
        else:
            update.message.reply_text("OTP salah. Silakan coba lagi.")

    elif current_state == 'awaiting_xut_choice':
        try:
            choice = int(text)
            selected_package = context.user_data['xut_packages'].get(choice)
            if selected_package:
                active_user = AuthInstance.get_active_user()
                if active_user:
                    update.message.reply_text(f"Anda memilih {selected_package['name']}. Memproses pembelian...")
                    # Panggil fungsi pembelian
                    purchase_result = settlement_multipayment(AuthInstance.api_key, active_user['tokens'], selected_package['code'], selected_package['price'], selected_package['name'])
                    if purchase_result and purchase_result.get("status") == "SUCCESS":
                        update.message.reply_text("Pembelian berhasil!")
                    else:
                        update.message.reply_text("Pembelian gagal. Silakan coba lagi.")
                else:
                    update.message.reply_text("Anda tidak login. Silakan coba lagi.")
                context.user_data.clear()
            else:
                update.message.reply_text("Pilihan paket tidak valid. Silakan coba lagi.")
        except ValueError:
            update.message.reply_text("Masukkan nomor paket yang valid.")

    elif current_state == 'awaiting_family_code':
        # Panggil fungsi untuk mendapatkan paket berdasarkan kode family
        packages = get_packages_by_family(text)
        if packages:
            text_response = "Paket Family tersedia:\n\n"
            for pkg in packages:
                text_response += f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}\n"
            update.message.reply_text(text_response)
        else:
            update.message.reply_text("Kode family tidak valid atau gagal mengambil data.")
        context.user_data.clear()

    # Cek apakah input adalah nomor telepon (inisiasi login)
    elif text.startswith("628") and len(text) > 9:
        if get_otp_and_handle_session(user_id, text):
            context.user_data['state'] = 'awaiting_otp'
            context.user_data['phone_number'] = text
            update.message.reply_text("Kode OTP telah dikirim. Silakan masukkan kode OTP Anda.")
        else:
            update.message.reply_text("Gagal mengirim OTP. Pastikan nomor benar atau coba lagi.")
    else:
        update.message.reply_text("Perintah tidak dikenali. Silakan gunakan /start atau /menu.")

# --- Flask Routes ---
@app.route('/')
def index():
    return jsonify({"message": "Bot is running! by @MzCoder"})

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

