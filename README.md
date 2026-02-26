# Discord DM Message Cleaner

**Discord’daki kendi mesajlarınızı DM sohbetlerinde toplu silen Python betiği.**  
**A Python script that bulk-deletes only your own messages in Discord DM conversations.**

---

## 📋 İçindekiler / Table of contents

- [Özellikler / Features](#-özellikler--features)
- [English](#-english)
- [Türkçe](#-türkçe)

---

## ✨ Özellikler / Features

| Özellik | Feature |
|--------|---------|
| Sadece **sizin** mesajlarınızı siler; karşı tarafın mesajlarına dokunmaz. | Deletes **only your** messages; leaves others’ messages intact. |
| Tüm DM’leri otomatik tespit eder (liste girmenize gerek yok). | Automatically detects all DMs (no manual list). |
| Silmek istemediğiniz kullanıcıları virgülle yazarak hariç tutabilirsiniz. | Exclude users by comma-separated usernames. |
| Dil seçimi: Türkçe veya İngilizce arayüz. | Language: Turkish or English UI. |
| Renkli terminal çıktısı (başlık, veri, uyarı ayrımı). | Colored terminal output. |
| **DRY RUN** modu: Önce hangi mesajların silineceğini listeler, silmez. | **DRY RUN** mode: Lists what would be deleted without deleting. |
| Rate limit koruması: Mesajlar arası ve DM geçişlerinde bekleme; 429’da otomatik duraklama. | Rate limit protection: Delays between deletes and DMs; auto-pause on 429. |
| 1:1 DM ve grup DM destekler. | Supports 1:1 and group DMs. |

---

## 🇬🇧 English

### What it does

- Uses the **Discord API** with your **user token** to act as you.
- Fetches **all** your DM channels (no hardcoded list).
- Lets you **exclude** specific users (e.g. `user1,user2`) so their DMs are skipped.
- For each non-excluded DM, finds **only messages sent by you** and deletes them one by one.
- Uses **human-like delays** and **429 handling** to reduce the risk of account flagging.

### Safe usage

1. **Token**: Storing or using a user token for automation may violate Discord’s ToS. Use at your own risk. Never commit `.env` or share your token.
2. **Dry run first**: Keep `DRY_RUN = True` in the script, run it, check the log. Only then set `DRY_RUN = False` for real deletions.
3. **No undo**: Deleted messages cannot be recovered.
4. **Scope**: The script does **not** remove or block friends; it only deletes your own messages inside DM channels.

### Setup

1. **Python 3.8+**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Token**
   - Copy `.env.example` to `.env`.
   - Set `DISCORD_TOKEN=your_token_here` in `.env`.
   - Do not commit `.env` (it is in `.gitignore`).

### Usage

1. Run the script:
   ```bash
   python discord_dm_cleaner.py
   ```
2. Choose language: **1** = Turkish, **2** = English.
3. Enter usernames to **exclude** (comma-separated, e.g. `alice,bob`), or leave empty to process all DMs.
4. The script will list all DMs (excluded ones are marked), then process each non-excluded DM: it shows how many of your messages will be deleted and deletes them (or only lists them if `DRY_RUN` is `True`).

### Configuration (in script)

| Variable | Default | Meaning |
|----------|---------|--------|
| `DRY_RUN` | `False` | `True` = only list, do not delete. |
| `MESSAGE_DELETE_DELAY_MIN/MAX` | `2.5` s | Pause between each message deletion. |
| `THREAD_SWITCH_DELAY_MIN/MAX` | `10`–`20` s | Pause when moving to the next DM. |
| `RATE_LIMIT_BACKOFF_SECONDS` | `120` | Pause when Discord returns 429, then retry. |

### Files

| File | Description |
|------|-------------|
| `discord_dm_cleaner.py` | Main script (config at top). |
| `requirements.txt` | Python dependencies. |
| `.env.example` | Example for `.env`; copy to `.env` and add your token. |
| `.env` | Your token (do not commit). |

### Disclaimer

This tool is for personal use. The author is not responsible for any action taken by Discord on your account. Use of a user token and automation may violate Discord’s Terms of Service. You assume all risk.

---

## 🇹🇷 Türkçe

### Ne yapar?

- **Discord API** ile **kullanıcı token’ınızı** kullanarak sizin adınıza işlem yapar.
- **Tüm** DM kanallarınızı otomatik alır (elle liste girmenize gerek yok).
- **Hariç tutmak** istediğiniz kullanıcıları (örn. `kullanici1,kullanici2`) virgülle yazarsanız o DM’lere dokunmaz.
- Hariç tutulmayan her DM’de **sadece sizin yazdığınız** mesajları bulur ve tek tek siler.
- Hesabın işaretlenme riskini azaltmak için **insan benzeri gecikmeler** ve **429 (rate limit)** durumunda otomatik bekleme kullanır.

### Güvenli kullanım

1. **Token**: Kullanıcı token’ı ile otomasyon Discord ToS’a aykırı olabilir. Risk size aittir. `.env` dosyasını asla paylaşmayın veya repoya eklemeyin.
2. **Önce dry run**: Script’te `DRY_RUN = True` bırakıp çalıştırın, çıktıyı kontrol edin. Ancak ondan sonra gerçek silme için `DRY_RUN = False` yapın.
3. **Geri alınamaz**: Silinen mesajlar kurtarılamaz.
4. **Kapsam**: Script arkadaş listenizi **silmez veya kimseyi engellemez**; yalnızca DM kanallarındaki kendi mesajlarınızı siler.

### Kurulum

1. **Python 3.8+**
2. **Bağımlılıkları yükleyin**
   ```bash
   pip install -r requirements.txt
   ```
3. **Token**
   - `.env.example` dosyasını `.env` olarak kopyalayın.
   - `.env` içinde `DISCORD_TOKEN=token_buraya` yazın.
   - `.env` dosyasını repoya eklemeyin (`.gitignore`’da yer alır).

### Kullanım

1. Script’i çalıştırın:
   ```bash
   python discord_dm_cleaner.py
   ```
2. Dil seçin: **1** = Türkçe, **2** = İngilizce.
3. **Hariç tutulacak** kullanıcı adlarını virgülle yazın (örn. `ali,veli`) veya hepsini işlemek için boş bırakın.
4. Script tüm DM’leri listeler (hariç tutulanlar işaretlenir), sonra hariç tutulmayan her DM için sizin mesaj sayısını gösterir ve siler (veya `DRY_RUN` `True` ise sadece listeler).

### Yapılandırma (script içinde)

| Değişken | Varsayılan | Anlamı |
|----------|------------|--------|
| `DRY_RUN` | `False` | `True` = sadece listele, silme. |
| `MESSAGE_DELETE_DELAY_MIN/MAX` | `2.5` sn | Her mesaj silmesi arasında bekleme. |
| `THREAD_SWITCH_DELAY_MIN/MAX` | `10`–`20` sn | Bir sonraki DM’e geçerken bekleme. |
| `RATE_LIMIT_BACKOFF_SECONDS` | `120` | Discord 429 döndüğünde bekleme süresi, sonra tekrar dene. |

### Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `discord_dm_cleaner.py` | Ana script (yapılandırma dosyanın başında). |
| `requirements.txt` | Python bağımlılıkları. |
| `.env.example` | `.env` örneği; `.env` kopyalayıp token’ınızı yazın. |
| `.env` | Token’ınız (repoya eklemeyin). |

### Sorumluluk reddi

Bu araç kişisel kullanım içindir. Geliştirici, Discord’un hesabınıza yönelik alacağı önlemlerden sorumlu değildir. Kullanıcı token’ı ve otomasyon Discord Hizmet Şartları’na aykırı olabilir. Tüm risk kullanıcıya aittir.
