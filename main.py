import os
import asyncio
from datetime import datetime, timezone, timedelta
import threading
from flask import Flask
import discord
from discord.ext import commands, tasks
from discord import app_commands

# 한국 표준시(KST: UTC+9) 정의
KST = timezone(timedelta(hours=9))

# Render의 Port Scan을 통과하기 위한 가짜 웹 서버 설정
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

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
    print(f"{bot.user} 로그인 완료")
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 커맨드 {len(synced)}개 동기화됨")
    except Exception as e:
        print(e)
    
    # 백그라운드 예약 작업 시작
    if not check_reservations.is_running():
        check_reservations.start()

# 1분마다 한국 시간 기준 예약 시간을 체크하는 백그라운드 루프
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
                print(f"[자동예약 실패] {user.name}님에게 DM을 보낼 수 없습니다. (권한 또는 공통 서버 없음)")
            except Exception as e:
                print(f"[자동예약 에러] {e}")
            
            del reservations[user_id]

@check_reservations.before_loop
async def before_check_reservations():
    await bot.wait_until_ready()


# --- /dm 커맨드 (Unknown interaction 방지 적용) ---
@bot.tree.command(name="dm", description="특정 유저에게 DM 보내기 (최대 1000개)")
@app_commands.describe(
    유저="DM을 받을 사람",
    보낼량="몇 번 보낼지 (최대 1000)",
    메시지="보낼 내용"
)
async def dm(interaction: discord.Interaction, 유저: discord.Member, 보낼량: int, 메시지: str):
    print(f"[명령어 사용] /dm | 사용자: {interaction.user.name} (ID: {interaction.user.id}) | 대상: {유저.name} | 횟수: {보낼량}")

    if 보낼량 < 1 or 보낼량 > 1000:
        await interaction.response.send_message("❌ 보낼량은 1부터 1000 사이의 숫자만 입력 가능합니다.", ephemeral=True)
        return

    # 1. 3초 제한 방지를 위해 먼저 응답 지연(defer) 처리 (ephemeral=True로 본인에게만 보이게 처리)
    await interaction.response.defer(ephemeral=True)
    
    success_count = 0
    
    for i in range(보낼량):
        try:
            await 유저.send(메시지)
            success_count += 1
            await asyncio.sleep(0.3) # API 제한 방지 딜레이
        except discord.Forbidden:
            print(f"DM 전송 실패: {유저.name}님에게 DM을 보낼 수 없습니다.")
            break
        except Exception as e:
            print(f"기타 에러 발생: {e}")
            break

    # 2. 지연 처리된 응답을 수정하여 완료 메시지 출력
    await interaction.followup.send(f"완료: {success_count}번 보냄", ephemeral=True)


# --- /자동예약 커맨드 ---
@bot.tree.command(name="자동예약", description="특정 유저에게 보낼 시간을 설정하여 DM 예약하기")
@app_commands.describe(
    보낼사람="DM을 받을 사람",
    보낼시간="보낼 시간 (예: 14:30 형식의 24시간제)",
    메시지="보낼 내용"
)
async def auto_reservation(interaction: discord.Interaction, 보낼사람: discord.Member, 보낼시간: str, 메시지: str):
    print(f"[명령어 사용] /자동예약 | 사용자: {interaction.user.name} (ID: {interaction.user.id}) | 대상: {보낼사람.name} | 시간: {보낼시간}")

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
async def cancel_reservation(interaction: discord.Interaction, 취소할사람: discord.Member):
    print(f"[명령어 사용] /예약취소 | 사용자: {interaction.user.name} (ID: {interaction.user.id}) | 대상: {취소할사람.name}")

    user_id = str(취소할사람.id)
    
    if user_id in reservations:
        del reservations[user_id]
        await interaction.response.send_message(f"✅ @{취소할사람.name}님의 예약이 성공적으로 취소되었습니다.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ @{취소할사람.name}님으로 등록된 활성 예약이 없습니다.", ephemeral=True)

# 봇 실행 (TOKEN 환경 변수 사용)
bot.run(os.environ.get("TOKEN"))
