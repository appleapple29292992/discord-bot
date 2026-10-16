import os
import asyncio
from datetime import datetime, timezone, timedelta
import threading
import socket
from flask import Flask, request
import discord
from discord.ext import commands, tasks
from discord import app_commands

# 한국 표준시(KST: UTC+9) 정의
KST = timezone(timedelta(hours=9))

# 봇이 실행 중인 서버의 IP 주소 가져오기
def get_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

SERVER_IP = get_server_ip()

# Render의 Port Scan을 통과하기 위한 가짜 웹 서버 설정 (이미지 포함)
app = Flask('')

@app.route('/')
def home():
    client_ip = request.remote_addr
    print(f"\033[92m[웹 접속] 외부 IP 접속 감지 | 클라이언트 IP: {client_ip} | 서버 IP: {SERVER_IP}\033[0m")
    
    # 웹사이트 접속 시 보여줄 HTML (이미지 중앙 배치)
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Justway Bot Status</title>
        <style>
            body {
                background-color: #121212;
                color: #ffffff;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                font-family: Arial, sans-serif;
            }
            h0 { color: #4CAF50; margin-bottom: 20px; }
            img {
                max-width: 80%;
                height: auto;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            }
        </style>
    </head>
    <body>
        <h1>🤖 Bot is alive & Running!</h1>
        <!-- 보내주신 이미지를 링크 형태로 웹에 삽입 -->
        <img src="https://i.imgur.com/your_image_link.jpg" alt="Justway Bot Image">
    </body>
    </html>
    """
    # 임시로 대표 이미지 URL을 쓰거나, 이미지를 호스팅하여 주소를 넣으실 수 있습니다.
    # 만약 직접 코드로 이미지를 띄우기 번거로우시다면 아래와 같이 이미지 주소를 대체할 수 있습니다.
    
    return f"""
    <div style="text-align: center; background: #111; color: #fff; padding: 50px; font-family: sans-serif;">
        <h1 style="color: #00ff00;">🤖 Bot is alive! (서버 정상 작동 중)</h1>
        <p>클라이언트 IP: {client_ip} | 서버 IP: {SERVER_IP}</p>
        <br>
        <!-- 보내주신 이미지를 웹 화면에 표시 -->
        <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe" style="max-width: 500px; border-radius: 10px;" alt="Bot Image">
    </div>
    """

def run_web():
    app.run(host='0.0.0.0', port=10000)

# 백그라운드에서 웹 서버를 실행시킵니다
threading.Thread(target=run_web).start()

# --- 디스코드 봇 코드 ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 예약 목록을 저장할 딕셔너리
reservations = {}

@bot.event
async def on_ready():
    print(f"{bot.user} 로그인 완료 (서버 IP: {SERVER_IP})")
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 커맨드 {len(synced)}개 동기화됨")
    except Exception as e:
        print(e)
    
    if not check_reservations.is_running():
        check_reservations.start()

@tasks.loop(seconds=60)
async def check_reservations():
    now = datetime.now(KST).strftime("%H:%M")
    
    for user_id, data in list(reservations.items()):
        if data["time"] == now:
            user = data["user"]
            message = data["message"]
            try:
                await user.send(message)
                print(f"[자동예약 성공] {user.name}님에게 예약된 DM 전송 완료")
            except discord.Forbidden:
                print(f"[자동예약 실패] {user.name}님에게 DM을 보낼 수 없습니다.")
            except Exception as e:
                print(f"[자동예약 에러] {e}")
            
            del reservations[user_id]

@check_reservations.before_loop
async def before_check_reservations():
    await bot.wait_until_ready()

# --- /dm 커맨드 ---
@bot.tree.command(name="dm", description="특정 유저에게 DM 보내기 (최대 1000개)")
@app_commands.describe(
    유저="DM을 받을 사람",
    보낼량="몇 번 보낼지 (최대 1000)",
    메시지="보낼 내용"
)
async def dm(interaction: discord.Interaction, 유저: discord.User, 보낼량: int, 메시지: str):
    print(f"\033[92m[명령어 실행] /dm | 유저 이름: {interaction.user.name} | 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 대상: {유저.name} | 횟수: {보낼량}\033[0m")

    if 보낼량 < 1 or 보낼량 > 1000:
        await interaction.response.send_message("❌ 보낼량은 1부터 1000 사이의 숫자만 입력 가능합니다.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    success_count = 0
    
    for i in range(보낼량):
        try:
            await 유저.send(메시지를)
            success_count += 1
            await asyncio.sleep(0.3)
        except discord.Forbidden:
            print(f"DM 전송 실패: {유저.name}님에게 DM을 보낼 수 없습니다.")
            break
        except Exception as e:
            print(f"기타 에러 발생: {e}")
            break

    await interaction.followup.send(f"완료: {success_count}번 보냄", ephemeral=True)

# --- /자동예약 커맨드 ---
@bot.tree.command(name="자동예약", description="특정 유저에게 보낼 시간을 설정하여 DM 예약하기")
@app_commands.describe(
    보낼사람="DM을 받을 사람",
    보낼시간="보낼 시간 (예: 14:30 형식의 24시간제)",
    메시지="보낼 내용"
)
async def auto_reservation(interaction: discord.Interaction, 보낼사람: discord.User, 보낼시간: str, 메시지: str):
    print(f"\033[92m[명령어 실행] /자동예약 | 유저 이름: {interaction.user.name} | 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 대상: {보낼사람.name} | 시간: {보낼시간}\033[0m")

    try:
        datetime.strptime(보낼시간, "%H:%M")
    except ValueError:
        await interaction.response.send_message("❌ 시간 형식은 `HH:MM` (예: `14:30` 또는 `09:15`) 형식으로 입력해주세요.", ephemeral=True)
        return

    reservations[str(보낼사람.id)] = {
        "user": 보낼사람,
        "time": 보낼시간,
        "message": 메시지
    }
    
    await interaction.response.send_message(f"✅ 성공적으로 예약되었습니다!\n- 대상: @{보낼사람.name}\n- 시간: {보낼시간} (한국 시간)\n- 내용: {메시지}", ephemeral=True)

# --- /예약취소 커맨드 ---
@bot.tree.command(name="예약취소", description="등록된 자동예약 취소하기")
@app_commands.describe(
    취소할사람="예약을 취소할 대상 유저"
)
async def cancel_reservation(interaction: discord.Interaction, 취소할사람: discord.User):
    print(f"\033[92m[명령어 실행] /예약취소 | 유저 이름: {interaction.user.name} | 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 대상: {취소할사람.name}\033[0m")

    user_id = str(취소할사람.id)
    
    if user_id in reservations:
        del reservations[user_id]
        await interaction.response.send_message(f"✅ @{취소할사람.name}님의 예약이 성공적으로 취소되었습니다.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ @{취소할사람.name}님으로 등록된 활성 예약이 없습니다.", ephemeral=True)

# 봇 실행
bot.run(os.environ.get("TOKEN"))
