# Gunakan base image Python resmi
FROM python:3.10-slim

# Set working directory di dalam container
WORKDIR /app

# Salin file requirements.txt dan instal dependensi
# Menggunakan langkah ini secara terpisah akan memanfaatkan Docker cache
# jika dependensi tidak berubah.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file proyek ke working directory
COPY . .

# Tetapkan variabel lingkungan yang diperlukan oleh aplikasi Anda.
# Anda harus mengganti nilai-nilai ini dengan milik Anda sendiri saat menjalankan container.
# Contoh: -e API_KEY="your_api_key_here"
ENV API_KEY="vT8tINqHaOxXbGE7eOWAhA=="
ENV AES_KEY_ASCII="5dccbf08920a5527"
ENV BASE_API_URL="https://api.myxl.xlaxiata.co.id"
ENV BASE_CIAM_URL="https://gede.ciam.xlaxiata.co.id"
ENV BASIC_AUTH="OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z"
ENV AX_DEVICE_ID="92fb44c0804233eb4d9e29f838223a14"
ENV AX_FP="18b4d589826af50241177961590e6693"
ENV UA="myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13"

# Jalankan skrip utama
CMD [ "python", "main.py" ]

