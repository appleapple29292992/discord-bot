
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

# Render의 Port Scan을 통과하기 위한 가짜 웹 서버 설정 (이미지를 배경 전체로 설정)
app = Flask('')

@app.route('/')
def home():
    client_ip = request.remote_addr
    print(f"\033[92m[웹 접속] 외부 IP 접속 감지 | 클라이언트 IP: {client_ip} | 서버 IP: {SERVER_IP}\033[0m")
    
    # 이미지를 자르지 않고 웹사이트 전체 배경으로 꽉 채우는 HTML/CSS
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Justway Bot</title>
        <style>
            body {{
                margin: 0;
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                font-family: sans-serif;
                /* 이미지를 배경으로 설정하고 잘리지 않게 조정 */
                background-image: url('https://i.ibb.co/KxphNsgy/1792145243681.jpg');
                background-size: contain; /* 이미지가 잘리지 않게 전체 비율 유지 */
                background-position: center;
                background-repeat: no-repeat;
                background-color: #121212; /* 이미지가 다 채우지 못하는 빈 공간 색상 */
            }}
            .info-box {{
                background: rgba(0, 0, 0, 0.7); /* 글씨가 잘 보이도록 반투명 검은 배경 추가 */
                padding: 20px 40px;
                border-radius: 10px;
                text-align: center;
                position: absolute;
                bottom: 30px;
            }}
            h1 {{ color: #00ff00; margin: 5px 0; font-size: 24px; }}
            p {{ color: #fff; margin: 5px 0; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="info-box">
            <h1>🤖 Bot is alive! (서버 정상 작동 중)</h1>
            <p>클라이언트 IP: {client_ip} | 서버 IP: {SERVER_IP}</p>
        </div>
    </body>
    </html>
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
            await 유저.send(메시지)
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
@bot.tree.command(name="자동예약", description="특정 유저에게 보낼 시간을 설정하여 DM 예약하기
