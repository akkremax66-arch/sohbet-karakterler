from flask import Flask, request, jsonify, render_template_string, redirect, Response
from openai import OpenAI
import datetime
import os
import json

app = Flask(__name__)

# x.ai (Grok) API bağlantı ayarları
client = OpenAI(
    api_key="**********", # BURAYI KENDİ ŞİFRENLE DEĞİŞTİR
    base_url="https://api.x.ai/v1"
)

# --- KARAKTER VERİTABANINI DIŞARIDAN OKU ---
with open("karakterler.json", "r", encoding="utf-8") as dosya:
    KARAKTERLER = json.load(dosya)

hafizalar = {}

# --- HTML ŞABLONLARI ---

ANASAYFA_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hanımlarla Sohbet Platformu</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #121212; margin: 0; padding: 50px 20px; text-align: center; }
        h1 { color: #ffffff; margin-bottom: 50px; font-weight: 300; font-size: 2.5rem; letter-spacing: 1px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; max-width: 1000px; margin: 0 auto; }
        .card { position: relative; height: 600px; border-radius: 15px; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-decoration: none; display: block; border-bottom: 6px solid; cursor: pointer;}
        .card img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94); }
        .card:hover img { transform: scale(1.08); }
        .card-overlay { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 50%, transparent 100%); padding: 40px 20px 20px; text-align: left; color: white; }
        .card h2 { margin: 0 0 5px 0; font-size: 26px; font-weight: 600; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); }
        .card p { margin: 0; color: #dcdcdc; font-size: 15px; font-weight: 300; }
        
        #login-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 100; justify-content: center; align-items: center; backdrop-filter: blur(5px); }
        .modal-content { background: #1e1e1e; padding: 40px; border-radius: 15px; width: 90%; max-width: 400px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 1px solid #333; }
        .modal-content h3 { color: white; margin-top: 0; font-size: 22px; font-weight: 400; margin-bottom: 25px;}
        .modal-content input { width: 85%; padding: 15px; border-radius: 8px; border: none; background: #2c2c2c; color: white; font-size: 16px; margin-bottom: 20px; outline: none; text-align: center; }
        .modal-content button { background: #8a1538; color: white; border: none; padding: 15px 30px; font-size: 16px; border-radius: 8px; cursor: pointer; width: 100%; transition: 0.2s; }
        .modal-content button:hover { background: #6b0f2a; }
        .close-btn { position: absolute; top: 15px; right: 20px; color: #777; font-size: 24px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Kiminle Sohbet Etmek İstersiniz?</h1>
    <div class="grid">
        {% for id, k in karakterler.items() %}
        <div onclick="openModal('{{ id }}')" class="card" style="border-bottom-color: {{ k.renk }}">
            <img src="{{ k.resim }}" alt="{{ k.isim }}">
            <div class="card-overlay">
                <h2>{{ k.isim }}</h2>
                <p>{{ k.unvan }}</p>
            </div>
        </div>
        {% endfor %}
    </div>

    <div id="login-modal">
        <div class="modal-content" style="position: relative;">
            <span class="close-btn" onclick="closeModal()">&times;</span>
            <h3>Kim O?</h3>
            <input type="text" id="username" placeholder="Adınızı giriniz..." onkeypress="if(event.key === 'Enter') startChat()">
            <button onclick="startChat()">Sohbete Başla</button>
        </div>
    </div>

    <script>
        let selectedCharacter = "";
        function openModal(characterId) {
            selectedCharacter = characterId;
            document.getElementById('login-modal').style.display = 'flex';
            document.getElementById('username').focus();
        }
        function closeModal() {
            document.getElementById('login-modal').style.display = 'none';
        }
        function startChat() {
            const username = document.getElementById('username').value.trim();
            if(username) {
                window.location.href = "/sohbet/" + selectedCharacter + "?kullanici=" + encodeURIComponent(username);
            } else {
                alert("Lütfen bir ad giriniz!");
            }
        }
    </script>
</body>
</html>
"""

SOHBET_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ karakter.isim }} ile Sohbet</title>
    <style>
        :root { --primary: {{ karakter.renk }}; --bg-color: #f0f2f5; --chat-bg: #ffffff; --bot-msg: #f8f9fa; --user-msg: #e8f4f8; --text-main: #333333; --border-color: #e0e0e0; }
        body, html { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); margin: 0; padding: 0; height: 100%; display: flex; justify-content: center; align-items: center; }
        .chat-container { width: 100%; max-width: 800px; background: var(--chat-bg); height: 100vh; display: flex; flex-direction: column; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        @media (min-width: 768px) { .chat-container { height: 90vh; border-radius: 12px; overflow: hidden; } }
        .header { background: #ffffff; padding: 12px 20px; display: flex; align-items: center; gap: 15px; border-bottom: 1px solid var(--border-color); z-index: 10; position: relative; }
        .back-btn { text-decoration: none; color: var(--primary); font-size: 24px; margin-right: 10px; font-weight: bold; }
        .header img { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 2px solid var(--primary); }
        .header-text { display: flex; flex-direction: column; }
        .header h2 { margin: 0; font-size: 17px; font-weight: 600; color: #2c3e50; }
        .header p { margin: 2px 0 0 0; font-size: 12px; color: #7f8c8d; }
        #chat-box { flex: 1; overflow-y: auto; padding: 20px; background-color: #fafafa; display: flex; flex-direction: column; gap: 12px; scroll-behavior: smooth; }
        .msg { padding: 12px 16px; border-radius: 18px; max-width: 85%; line-height: 1.5; font-size: 15px; color: var(--text-main); word-wrap: break-word; white-space: pre-wrap; }
        .user { background: var(--user-msg); align-self: flex-end; border-bottom-right-radius: 4px; }
        .bot { background: var(--bot-msg); border: 1px solid var(--border-color); align-self: flex-start; border-bottom-left-radius: 4px; }
        
        .preview-area { display: none; padding: 10px 20px; background: #fff; border-top: 1px solid var(--border-color); align-items: center; justify-content: space-between; }
        .preview-area img { max-height: 80px; border-radius: 8px; border: 1px solid #ddd; }
        .remove-img { color: #e74c3c; cursor: pointer; font-size: 14px; font-weight: bold; padding: 5px 10px; }
        
        .input-area { display: flex; padding: 12px; background: #ffffff; border-top: 1px solid var(--border-color); gap: 10px; align-items: center; }
        
        .attach-btn { background: #f0f2f5; color: #555; border: 1px solid #ddd; width: 44px; height: 44px; border-radius: 50%; cursor: pointer; display: flex; justify-content: center; align-items: center; flex-shrink: 0; transition: 0.2s; }
        .attach-btn:hover { background: #e4e6e9; color: var(--primary); border-color: var(--primary); }
        
        input[type="text"] { flex: 1; padding: 12px 18px; border: 1px solid #dcdcdc; border-radius: 24px; outline: none; font-size: 15px; background: #f8f9fa; }
        input[type="text"]:focus { border-color: var(--primary); background: #ffffff; }
        
        .send-btn { background: var(--primary); color: #ffffff; border: none; width: 44px; height: 44px; border-radius: 50%; cursor: pointer; display: flex; justify-content: center; align-items: center; flex-shrink: 0; }
        
        .typing { display: flex; align-items: center; gap: 4px; padding: 10px; }
        .dot { width: 6px; height: 6px; background-color: #999; border-radius: 50%; animation: blink 1.4s infinite both; }
        .dot:nth-child(1) { animation-delay: 0.2s; }
        .dot:nth-child(2) { animation-delay: 0.4s; }
        .dot:nth-child(3) { animation-delay: 0.6s; }
        @keyframes blink { 0% { opacity: .2; } 20% { opacity: 1; } 100% { opacity: .2; } }
        
        .intro-gallery { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
        .intro-gallery img { max-height: 140px; border-radius: 8px; border: 1px solid #dcdcdc; cursor: zoom-in; transition: transform 0.2s; }
        .intro-gallery img:hover { transform: scale(1.03); border-color: var(--primary); }

        /* YENİ: Görsel Büyütme (Lightbox) Tasarımı */
        #lightbox-modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0, 0, 0, 0.85); z-index: 9999;
            justify-content: center; align-items: center; cursor: zoom-out;
            backdrop-filter: blur(5px);
        }
        #lightbox-img {
            max-width: 90%; max-height: 90%; border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            animation: zoomIn 0.3s ease;
        }
        .lightbox-close {
            position: absolute; top: 20px; right: 30px; color: white;
            font-size: 40px; font-weight: bold; cursor: pointer;
        }
        @keyframes zoomIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    </style>
</head>
<body>
    <!-- YENİ: Gizli Lightbox Modal -->
    <div id="lightbox-modal" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <img id="lightbox-img" src="">
    </div>

    <div class="chat-container">
        <div class="header">
            <a href="/" class="back-btn">&#8592;</a>
            <img src="{{ karakter.resim }}" alt="{{ karakter.isim }}">
            <div class="header-text">
                <h2>{{ karakter.isim }}</h2>
                <p>Kullanıcı: {{ kullanici }}</p>
            </div>
        </div>
        
        <div id="chat-box">
            <div class="msg bot">
                {{ karakter.ilk_mesaj }}
                
                {% if 'ek_fotograflar' in karakter %}
                <div class="intro-gallery">
                    <!-- Tıklayınca Lightbox'ı açan fonksiyon eklendi -->
                    {% for foto in karakter.ek_fotograflar %}
                    <img src="{{ foto }}" alt="Karakter Fotoğrafı" onclick="openLightbox(this.src)">
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="preview-area" id="preview-area">
            <img id="image-preview" src="" alt="Önizleme">
            <span class="remove-img" onclick="removeImage()">✖ İptal Et</span>
        </div>

        <div class="input-area">
            <input type="file" id="file-input" accept="image/*" style="display: none;" onchange="handleImage(event)">
            <button class="attach-btn" type="button" onclick="document.getElementById('file-input').click()" title="Görsel Yükle">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
            </button>
            <input type="text" id="user-input" placeholder="Mesaj veya fotoğraf..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button class="send-btn" onclick="sendMessage()">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="white"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
            </button>
        </div>
    </div>

    <script>
        const karakterId = "{{ karakter.id }}";
        const kullaniciAdi = "{{ kullanici }}";
        let base64Image = null;

        // YENİ: Lightbox Fonksiyonları
        function openLightbox(imgSrc) {
            document.getElementById('lightbox-img').src = imgSrc;
            document.getElementById('lightbox-modal').style.display = 'flex';
        }
        function closeLightbox() {
            document.getElementById('lightbox-modal').style.display = 'none';
        }

        function handleImage(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                base64Image = e.target.result.split(',')[1];
                document.getElementById('image-preview').src = e.target.result;
                document.getElementById('preview-area').style.display = 'flex';
            };
            reader.readAsDataURL(file);
        }

        function removeImage() {
            base64Image = null;
            document.getElementById('file-input').value = '';
            document.getElementById('preview-area').style.display = 'none';
        }

        async function sendMessage() {
            const inputField = document.getElementById('user-input');
            const message = inputField.value.trim();
            if (!message && !base64Image) return;

            const chatBox = document.getElementById('chat-box');
            
            let userHtml = `<div class="msg user">`;
            if (base64Image) {
                userHtml += `<img src="data:image/jpeg;base64,${base64Image}" style="max-width: 100%; border-radius: 8px; margin-bottom: 5px;"><br>`;
            }
            if (message) { userHtml += message; }
            userHtml += `</div>`;
            chatBox.innerHTML += userHtml;
            chatBox.scrollTop = chatBox.scrollHeight;

            inputField.value = '';
            const currentImg = base64Image;
            removeImage();

            const botMsgContainer = document.createElement('div');
            botMsgContainer.className = 'msg bot';
            botMsgContainer.innerHTML = `<div class="typing"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
            chatBox.appendChild(botMsgContainer);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/api/chat_stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: message, 
                        karakter_id: karakterId, 
                        kullanici: kullaniciAdi,
                        image: currentImg
                    })
                });

                botMsgContainer.innerHTML = "";
                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunkText = decoder.decode(value, { stream: true });
                    botMsgContainer.innerHTML += chunkText;
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                
            } catch (error) {
                botMsgContainer.innerHTML = `<span style="color:red;">(Hata: Bağlantı koptu.)</span>`;
            }
        }
    </script>
</body>
</html>
"""

# --- FLASK YOLLARI ---

@app.route('/')
def home():
    return render_template_string(ANASAYFA_HTML, karakterler=KARAKTERLER)

@app.route('/sohbet/<karakter_id>')
def chat_page(karakter_id):
    if karakter_id not in KARAKTERLER:
        return "Karakter bulunamadı!", 404
    kullanici_adi = request.args.get('kullanici')
    if not kullanici_adi: return redirect('/')
    karakter = KARAKTERLER[karakter_id]
    oturum_anahtari = f"{karakter_id}_{kullanici_adi}"
    hafizalar[oturum_anahtari] = [{"role": "system", "content": karakter["sistem_mesaji"]}]
    
    return render_template_string(SOHBET_HTML, karakter=karakter, kullanici=kullanici_adi)

@app.route('/api/chat_stream', methods=['POST'])
def api_chat_stream():
    veri = request.json
    user_message = veri.get('message', '')
    karakter_id = veri['karakter_id']
    kullanici_adi = veri['kullanici']
    image_base64 = veri.get('image')
    
    user_content = []
    if user_message:
        user_content.append({"type": "text", "text": user_message})
    elif image_base64:
        user_content.append({"type": "text", "text": "Bu görsele bak ve karakterine göre yorumla."})
        
    if image_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        })

    oturum_anahtari = f"{karakter_id}_{kullanici_adi}"
    gecmis = hafizalar.get(oturum_anahtari, [])
    gecmis.append({"role": "user", "content": user_content})
    
    # MODELLERİ BURAYA YAZIN
    normal_model = "grok-4-1-fast-reasoning" 
    goren_model = "grok-4-1-fast-reasoning"  
    
    kullanilacak_model = goren_model if image_base64 else normal_model

    def generate_response():
        bot_reply = ""
        hata_durumu = False
        
        try:
            response = client.chat.completions.create(
                messages=gecmis,
                model=kullanilacak_model, 
                temperature=0.7,
                stream=True 
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    kelime = chunk.choices[0].delta.content
                    bot_reply += kelime
                    yield kelime
                    
        except Exception as e:
            hata_mesaji = str(e)
            print("Hata Detayı:", hata_mesaji)
            hata_durumu = True
            bot_reply = f"\n[Ağam, divanda karışıklık çıktı: {hata_mesaji}]"
            yield bot_reply

        if hata_durumu:
            gecmis.pop()
        else:
            gecmis.append({"role": "assistant", "content": bot_reply})
            
        hafizalar[oturum_anahtari] = gecmis

        zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bugun = datetime.datetime.now().strftime("%Y-%m-%d") 
        if not os.path.exists("kayitlar"): os.makedirs("kayitlar")
        dosya_adi = f"kayitlar/{karakter_id}_{kullanici_adi}_{bugun}.txt"
        kayit_notu = f"[GÖRSEL] {user_message}" if image_base64 else user_message

        with open(dosya_adi, "a", encoding="utf-8") as dosya:
            dosya.write(f"[{zaman}] {kullanici_adi.upper()}: {kayit_notu}\n")
            dosya.write(f"[{zaman}] BOT: {bot_reply}\n")
            dosya.write("-" * 50 + "\n")

    return Response(generate_response(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)
