import os
import sys
import discord
import youtube_dl
from discord.ext import commands, tasks
from discord.voice_client import VoiceClient
from random import choice

# TODO: 1. Повтор дорожки
#       2. Формирование очеереди

Token = ' ' # Токен бота

youtube_dl.utils.bug_reports_message = lambda: '' # Ваще хз чо за херня, но судя по названию, что-то о репортах ошибок

# Настройка youtube_dl. Стоковые, ничего не менял 
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # Привязан к IPv4 и IPv6, но тут вроде как иногда что-то ломается, хз
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Это тоже стоковая настройка youtube_dl (Боже, храни stackoverflow)
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Символ для команд бот: либо "!", либо упоминание через @
miku = commands.Bot(command_prefix=commands.when_mentioned_or('!'))

status = ['Диджея'] # Просто для прикола (Играет в Диджея)
queue = []

# Вывод в консоль о запуске бота
@miku.event
async def on_ready():
    change_status.start()
    print('Бот запущен')

# TODO: По идее, это должно работать при подключении нового пользователя к каналу, но на деле не работает, позже гляну
@miku.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.channels, name='test-for-test')
    await channel.send(f'Привет, {ctx.author.mention}!). Можешь написать **!help**, чтобы посмотреть команды')


# TODO: Проверка пинга....Хз зачем, но прикольно 
'''       
@client.command(name='ping', help='This command returns the latency')
async def ping(ctx):
    await ctx.send(f'Latency: {round(client.latency * 1000)}ms')
'''

# Стандартная команда
@miku.command(name='привет', help='Это я просто отвечаю тебе на приветствие)')
async def привет(ctx):
    await ctx.send(f'Приветик, {ctx.author.mention}! 😄')


# Команда забавы ради. Чисто поржать xD
@miku.command(name='credits', help='Эта команда покажет тебе авторов бота (вернее, автора)')
async def credits(ctx):
    myid = '<@313010391842029578>'
    await ctx.send('Код отчасти ||спизжен||')
    await ctx.send('Но допиливал и переделывал его ' + myid)
    await ctx.send('Так что он автор и красавчикващереспект)')
 

# Команда присоединения бота к голосовому каналу
@miku.command(name='join', help='Напиши после !join название голосового канала и я сразу буду там!')
async def join(ctx, channel: discord.VoiceChannel):
        """Присоединяется к каналу"""
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()
        #await ctx.send('А вот и я! :D') # TODO: Потом доработать вывод названия канала, в который присоединяется бот


# Самая главная команда на воспроизведение музыки из видоса по ссылке. Работает в режиме стриминга аудио (был вариант с предзагрузкой, но это дичь полная)
@miku.command(name='play', help='Очевидно) Вставь ссылку с ютуба и наслаждайся!')
async def play(ctx, url):
    global queue
    await ctx.send('Дай мне секунду...')
    server = ctx.message.guild
    voice_channel = server.voice_client
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=miku.loop, stream=True)
        voice_channel.play(player, after=lambda e: print('Ошибка: %s' % e) if e else None)
    await ctx.send(':musical_note: **Сейчас играет:** {}'.format(player.title))
    del(queue[0])



@miku.command(name='add', help='Эта команда добавляет трек в плейлист на проигрывание')
async def add(ctx, url):
    global queue
    queue.append(url)
    await ctx.send(f'`{url}` добавлен в плейлист!)')



@miku.command(name='remove', help='Эта команда убирает трек из очереди')
async def remove(ctx, number):
    global queue
    try:
        del(queue[int(number)])
        await ctx.send(f'Теперь плейлист выглядит так: `{queue}!`')
    except:
        await ctx.send('Плейлист уже **пуст** :/ Добавь в него что-нибудь! Послушаем вместе! :D')



@miku.command(name='playlist', help='Этак команда выводит плейлист, чтобы ты всегда помнил, что будет играть дальше)')
async def view(ctx):
    await ctx.send(f'Сейчас плейлист выглядит так: `{queue}!`')


# Просто команда паузы
@miku.command(name='pause', help='Ставлю на паузу')
async def pause(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.pause()
    await ctx.send('Пауза')


# Воспроизведение
@miku.command(name='resume', help='Включаю дальше')
async def resume(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.resume()
    await ctx.send('Продолжаем')
    await ctx.send(':musical_note: **Сейчас играет:** {}'.format(player.title))


# Команда для отключения бота из канала (перед этим рекомендуется прописывать !stop)
@miku.command(name='leave', help='Эта команда заставит меня выйти из канала. Звучит грубо, но что поделать)')
async def leave(ctx):
    await ctx.send('(*улыбаясь*) Зови в любое время!)')
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()
   

# Останавливает проигрование текущей дорожки, позволяя включить следующую
@miku.command(name='stop', help='Это полностью остановить играющий трек, чтобы можно было запустить новый')
async def stop(ctx):
    await ctx.send('Закончим? Ну, давай)')
    server = ctx.message.guild
    voice_channel = server.voice_client
    voice_channel.stop()


# Функция для обновления статуса "Играет в..."
@tasks.loop(seconds=20)
async def change_status():
    await miku.change_presence(activity=discord.Game(choice(status)))

miku.run(Token)