import asyncio
from datetime import datetime, timedelta, timezone
import os
import socket
import threading
from discord import app_commands
import discord
from discord.ext import commands, tasks
from flask import Flask, request

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

# Render의 Port Scan을 통과하기 위한 가짜 웹 서버 설정 (HTML 구문 수정)
app = Flask("")


@app.route("/")
def home():
  client_ip = request.remote_addr
  print(
      f"\033[92m[웹 접속] 외부 IP 접속 감지 | 클라이언트 IP: {client_ip} | 서버"
      f" IP: {SERVER_IP}\033[0m"
  )

  html = (
      """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Justway Bot</title>
        <style>
            body {
                margin: 0;
                height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                font-family: sans-serif;
                background-image: url('https://i.ibb.co/KxphNsgy/1792145243681.jpg');
                background-size: contain;
                background-position: center;
                background-repeat: no-repeat;
                background-color: #121212;
            }
            .info-box {
                background: rgba(0, 0, 0, 0.7);
                padding: 20px 40px;
                border-radius: 10px;
                text-align: center;
                position: absolute;
                bottom: 30px;
            }
            h1 { color: #00ff00; margin: 5px 0; font-size: 24px; }
            p { color: #fff; margin: 5px 0; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="info-box">
            <h1>🤖 Bot is alive! (서버 정상 작동 중)</h1>
            <p>클라이언트 IP: """
      + str(client_ip)
      + """ | 서버 IP: """
      + str(SERVER_IP)
      + """</p>
        </div>
    </body>
    </html>
    """
  )
  return html


def run_web():
  app.run(host="0.0.0.0", port=10000)


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


# --- /말하기 커맨드 (추가됨) ---
@bot.tree.command(
    name="말하기", description="채팅에 지정한 내용을 횟수만큼 반복해서 보냅니다 (최대 50개)"
)
@app_commands.describe(말할내용="봇이 말할 메시지 내용", 보낼량="반복해서 보낼 횟수 (1~50)")
async def speak(interaction: discord.Interaction, 말할내용: str, 보낼량: int):
  print(
      f"\033[92m[명령어 실행] /말하기 | 유저 이름: {interaction.user.name} |"
      f" 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 횟수:"
      f" {보낼량}\033[0m"
  )

  if 보낼량 < 1 or 보낼량 > 50:
    await interaction.response.send_message(
        "❌ 보낼량은 1부터 50 사이의 숫자만 입력 가능합니다.", ephemeral=True
    )
    return

  await interaction.response.defer(ephemeral=True)

  for i in range(보낼량):
    try:
      await interaction.channel.send(말할내용)
      await asyncio.sleep(0.3)  # 메시지 전송 간 딜레이 (디스코드 레이트 리밋 방지)
    except Exception as e:
      print(f"메시지 전송 에러: {e}")
      break

  await interaction.followup.send(
      f"✅ 성공적으로 총 {보낼량개의} 메시지를 보냈습니다.", ephemeral=True
  )


# --- /dm 커맨드 ---
@bot.tree.command(
    name="dm", description="특정 유저에게 DM 보내기 (최대 1000개)"
)
@app_commands.describe(
    유저="DM을 받을 사람", 보낼량="몇 번 보낼지 (최대 1000)", 메시지="보낼 내용"
)
async def dm(
    interaction: discord.Interaction,
    유저: discord.User,
    보낼량: int,
    메시지: str,
):
  print(
      f"\033[92m[명령어 실행] /dm | 유저 이름: {interaction.user.name} |"
      f" 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 대상:"
      f" {유저.name} | 횟수: {보낼량}\033[0m"
  )

  if 보낼량 < 1 or 보낼량 > 1000:
    await interaction.response.send_message(
        "❌ 보낼량은 1부터 1000 사이의 숫자만 입력 가능합니다.", ephemeral=True
    )
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

  await interaction.followup.send(
      f"완료: {success_count}번 보냄", ephemeral=True
  )


# --- /자동예약 커맨드 ---
@bot.tree.command(
    name="자동예약", description="특정 유저에게 보낼 시간을 설정하여 DM 예약하기"
)
@app_commands.describe(
    보낼사람="DM을 받을 사람",
    보낼시간="보낼 시간 (예: 14:30 형식의 24시간제)",
    메시지="보낼 내용",
)
async def auto_reservation(
    interaction: discord.Interaction,
    보낼사람: discord.User,
    보낼시간: str,
    메시지: str,
):
  print(
      f"\033[92m[명령어 실행] /자동예약 | 유저 이름: {interaction.user.name} |"
      f" 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 대상:"
      f" {보낼사람.name} | 시간: {보낼시간}\033[0m"
  )

  try:
    datetime.strptime(보낼시간, "%H:%M")
  except ValueError:
    await interaction.response.send_message(
        "❌ 시간 형식은 `HH:MM` (예: `14:30` 또는 `09:15`) 형식으로 입력해주세요.",
        ephemeral=True,
    )
    return

  reservations[str(보낼사람.id)] = {
      "user": 보낼사람,
      "time": 보낼시간,
      "message": 메시지,
  }

  await interaction.response.send_message(
      f"✅ 성공적으로 예약되었습니다!\n- 대상: @{보낼사람.name}\n- 시간: {보낼시간}"
      f" (한국 시간)\n- 내용: {메시지}",
      ephemeral=True,
  )


# --- /예약취소 커맨드 ---
@bot.tree.command(name="예약취소", description="등록된 자동예약 취소하기")
@app_commands.describe(취소할사람="예약을 취소할 대상 유저")
async def cancel_reservation(
    interaction: discord.Interaction, 취소할사람: discord.User
):
  print(
      f"\033[92m[명령어 실행] /예약취소 | 유저 이름: {interaction.user.name} |"
      f" 디스코드 ID: {interaction.user.id} | 서버 IP: {SERVER_IP} | 대상:"
      f" {취소할사람.name}\033[0m"
  )

  user_id = str(취소할사람.id)

  if user_id in reservations:
    del reservations[user_id]
    await interaction.response.send_message(
        f"✅ @{취소할사람.name}님의 예약이 성공적으로 취소되었습니다.", ephemeral=True
    )
  else:
    await interaction.response.send_message(
        f"❌ @{취소할사람.name}님으로 등록된 활성 예약이 없습니다.", ephemeral=True
    )


# 봇 실행
bot.run(os.environ.get("TOKEN"))
