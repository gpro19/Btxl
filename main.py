import os
import threading
import logging
from flask import Flask, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext,
    MessageHandler, Filters, JobQueue
)



# Impor semua fungsi dari file Anda yang sudah ada
from auth_helper import AuthInstance, get_otp_and_handle_session, submit_otp_and_login_session
from my_package import get_my_packages_data
from paket_xut import get_package_xut
from paket_custom_family import get_packages_by_family
from api_request import get_balance
from purchase_api import get_payment_methods, settlement_multipayment

# Aktifkan logging untuk melacak bot
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Ambil token bot dari variabel lingkungan untuk keamanan
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8319444433:AAHRLxXy4hqGnXsVLR_vSwCIsnSirX_vwcE")

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# --- Handler untuk Perintah Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan saat perintah /start diberikan."""
    await update.message.reply_text(
        "Selamat datang! Kirim nomor XL Anda (diawali 628) untuk login, atau gunakan /menu untuk melihat opsi."
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await update.message.reply_text(f"{balance_text}\n{menu_text}")
    else:
        await update.message.reply_text("Anda belum login. Silakan kirim nomor XL Anda untuk login.")

async def cekpaket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan menampilkan paket yang dimiliki pengguna."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        await update.message.reply_text("Silakan login terlebih dahulu.")
        return

    await update.message.reply_text("Memuat paket Anda, mohon tunggu...")
    packages = get_my_packages_data()
    
    if packages:
        text = "Paket Anda:\n\n"
        for i, pkg in enumerate(packages):
            text += f"{i+1}. {pkg['name']} (Quota: {pkg['remaining_quota']})\n"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("Gagal mengambil paket. Silakan coba lagi.")


async def xut(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar paket XUT."""
    active_user = AuthInstance.get_active_user()
    if not active_user:
        await update.message.reply_text("Silakan login terlebih dahulu.")
        return

    packages = get_package_xut()
    if packages:
        text = "Paket Unli Turbo (XUT):\n\n"
        for pkg in packages:
            text += f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}\n"
        await update.message.reply_text(text)
        await update.message.reply_text("Pilih paket dengan mengirimkan nomornya. Contoh: `1`")
        
        # Simpan paket di context untuk diproses di langkah berikutnya
        context.user_data['xut_packages'] = {p['number']: p for p in packages}
        context.user_data['state'] = 'awaiting_xut_choice'
        
    else:
        await update.message.reply_text("Gagal mengambil paket XUT.")

async def family(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Meminta kode family dari pengguna."""
    await update.message.reply_text("Silakan kirim kode family yang ingin Anda lihat paketnya.")
    context.user_data['state'] = 'awaiting_family_code'
    
async def gantiakun(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menghapus pengguna aktif dan memulai ulang proses login."""
    AuthInstance.set_active_user(None)
    await update.message.reply_text("Akun berhasil diganti. Silakan kirim nomor baru untuk login.")

# --- Handler untuk Pesan Teks ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani pesan teks apa pun, termasuk alur login dan pembelian."""
    text = update.message.text
    user_id = update.effective_user.id
    current_state = context.user_data.get('state')

    if current_state == 'awaiting_otp':
        phone_number = context.user_data.get('phone_number')
        if submit_otp_and_login_session(user_id, phone_number, text):
            await update.message.reply_text("Login berhasil! Gunakan /menu untuk melihat opsi.")
            context.user_data.clear() # Hapus state
        else:
            await update.message.reply_text("OTP salah. Silakan coba lagi.")

    elif current_state == 'awaiting_xut_choice':
        try:
            choice = int(text)
            selected_package = context.user_data['xut_packages'].get(choice)
            if selected_package:
                active_user = AuthInstance.get_active_user()
                if active_user:
                    await update.message.reply_text(f"Anda memilih {selected_package['name']}. Memproses pembelian...")
                    # Panggil fungsi pembelian
                    purchase_result = settlement_multipayment(AuthInstance.api_key, active_user['tokens'], selected_package['code'], selected_package['price'], selected_package['name'])
                    if purchase_result and purchase_result.get("status") == "SUCCESS":
                        await update.message.reply_text("Pembelian berhasil!")
                    else:
                        await update.message.reply_text("Pembelian gagal. Silakan coba lagi.")
                else:
                    await update.message.reply_text("Anda tidak login. Silakan coba lagi.")
                context.user_data.clear()
            else:
                await update.message.reply_text("Pilihan paket tidak valid. Silakan coba lagi.")
        except ValueError:
            await update.message.reply_text("Masukkan nomor paket yang valid.")
    
    elif current_state == 'awaiting_family_code':
        # Panggil fungsi untuk mendapatkan paket berdasarkan kode family
        packages = get_packages_by_family(text)
        if packages:
            text_response = "Paket Family tersedia:\n\n"
            for pkg in packages:
                text_response += f"{pkg['number']}. {pkg['name']} - Rp {pkg['price']}\n"
            await update.message.reply_text(text_response)
        else:
            await update.message.reply_text("Kode family tidak valid atau gagal mengambil data.")
        context.user_data.clear()

    # Cek apakah input adalah nomor telepon (inisiasi login)
    elif text.startswith("628") and len(text) > 9:
        if get_otp_and_handle_session(user_id, text):
            context.user_data['state'] = 'awaiting_otp'
            context.user_data['phone_number'] = text
            await update.message.reply_text("Kode OTP telah dikirim. Silakan masukkan kode OTP Anda.")
        else:
            await update.message.reply_text("Gagal mengirim OTP. Pastikan nomor benar atau coba lagi.")
    else:
        await update.message.reply_text("Perintah tidak dikenali. Silakan gunakan /start atau /menu.")

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
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Daftarkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("cekpaket", cekpaket))
    application.add_handler(CommandHandler("xut", xut))
    application.add_handler(CommandHandler("family", family))
    application.add_handler(CommandHandler("gantiakun", gantiakun))
    
    # Handler pesan teks (non-perintah)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Mulai bot
    application.run_polling()
    
if __name__ == "__main__":
    # Mulai Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Mulai bot di main thread
    main()

