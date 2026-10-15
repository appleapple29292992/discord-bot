import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} 로그인 완료")
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 커맨드 {len(synced)}개 동기화됨")
    except Exception as e:
        print(e)

@bot.tree.command(name="dm", description="특정 유저에게 DM 보내기")
@app_commands.describe(
    유저="DM을 받을 사람",
    보낼량="몇 번 보낼지 (숫자)",
    메시지="보낼 내용"
)
async def dm(interaction: discord.Interaction, 유저: discord.Member, 보낼량: int, 메시지: str):
    if 보낼량 < 1 or 보낼량 > 20:
        await interaction.response.send_message("보낼량은 1\~20 사이로 해줘.", ephemeral=True)
        return

    await interaction.response.send_message(f"{유저.mention}에게 {보낼량}번 보내는 중...", ephemeral=True)

    success = 0
    for i in range(보낼량):
        try:
            await 유저.send(메시지)
            success += 1
        except:
            break

    await interaction.followup.send(f"완료: {success}번 보냄", ephemeral=True)


bot.run(os.environ.get("TOKEN"))
