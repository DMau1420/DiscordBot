import os
import subprocess
import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import time
import asyncio

# Configuración
TOKEN = "" # Token de tu bot
SERVER_IP = "" #ip de tu servidor
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(BASE_DIR, "McServer", "run.bat") #o run.sh en linux

# Tiempos en segundos
CHECK_INTERVAL = 300  # 5 minutos
WARNING_TIME = 600    # 10 minutos (aviso a los 5 min sin jugadores)
SHUTDOWN_TIME = 900   # 15 minutos

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

class ServerManager:
    def __init__(self):
        self.last_player_time = time.time()
        self.server_process = None
    
    def start_server(self):
        """Inicia el servidor de Minecraft en Linux"""
        try:
            # Inicia el servidor en Linux
            self.server_process = subprocess.Popen(
                "/bin/bash /root/run.sh",
                shell=True
            )
            return True, "⚡ Iniciando servidor..."
        except Exception as e:
            return False, f"❌ Error al abrir el servidor: {e}"
    
    def stop_server(self):
        """Detiene el servidor de Minecraft en Linux"""
        try:
            # Detener el proceso del servidor si está corriendo
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait()
                self.server_process = None
            
            # Asegurarse de matar cualquier proceso Java restante
            subprocess.run(["pkill", "-f", "java"], stderr=subprocess.DEVNULL)
            return True, "🛑 Servidor cerrado correctamente"
        except Exception as e:
            return False, f"❌ Error al cerrar el servidor: {e}"
    
    def get_status(self):
        """Obtiene el estado del servidor usando mcstatus"""
        try:
            server = JavaServer.lookup(SERVER_IP)
            status = server.status()
            return {
                "online": True,
                "players": status.players.online,
                "max_players": status.players.max,
                "version": status.version.name,
                "latency": status.latency,
                "motd": status.description
            }
        except:
            return {"online": False}

manager = ServerManager()

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_inactivity():
    """Verifica la inactividad del servidor cada 5 minutos"""
    try:
        channel = bot.get_channel(1362164980618756106)  # Canal de notificaciones
        status = manager.get_status()
        
        # Si el servidor está apagado, reiniciamos el contador
        if not status["online"]:
            manager.last_player_time = time.time()
            return
        
        # Si hay jugadores, actualizamos el tiempo
        if status["players"] > 0:
            manager.last_player_time = time.time()
            return
        
        # Calculamos tiempo inactivo
        inactive_time = time.time() - manager.last_player_time
        
        # Enviamos advertencia a los 10 minutos
        if WARNING_TIME <= inactive_time < WARNING_TIME + CHECK_INTERVAL:
            if channel:
                remaining = (SHUTDOWN_TIME - inactive_time) / 60
                await channel.send(
                    f"⚠️ El servidor se cerrará en {int(remaining)} minutos "
                    "por inactividad. ¡Conéctate para mantenerlo activo!"
                )
        
        # Cerramos el servidor a los 15 minutos
        if inactive_time >= SHUTDOWN_TIME:
            if channel:
                await channel.send("🛑 Cerrando servidor por inactividad (15 mins sin jugadores)")
            manager.stop_server()
            manager.last_player_time = time.time()
            
    except Exception as e:
        print(f"Error en check_inactivity: {e}")
        if 'channel' in locals() and channel:
            await channel.send(f"❌ Error al verificar inactividad: {str(e)}")

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    if not check_inactivity.is_running():
        check_inactivity.start()

@bot.command(name="abrir")
async def abrir(ctx):
    """Inicia el servidor de Minecraft"""
    status = manager.get_status()
    if status["online"]:
        await ctx.send("✅ El servidor ya está en línea!")
        return
    
    success, message = manager.start_server()
    await ctx.send(message)
    
    # Verificar cuando esté listo
    for i in range(1, 25):  # 12 intentos (60 segundos máximo)
        await asyncio.sleep(5)
        status = manager.get_status()
        if status["online"]:
            await ctx.send(f"✅ Servidor listo después de {i*5} segundos!")
            return
        await ctx.send(f"⏳ Verificando... ({i*5} segundos)")
    
    await ctx.send("⚠️ El servidor no responde después de 1 minuto")

@bot.command(name="cerrar")
async def cerrar(ctx):
    """Detiene el servidor de Minecraft"""
    status = manager.get_status()
    
    # Verificar jugadores conectados
    if status["online"] and status["players"] > 0:
        confirm = await ctx.send(
            f"⚠️ Hay {status['players']} jugadores conectados. "
            "¿Estás seguro de querer cerrar el servidor? (reacciona con 👍)"
        )
        await confirm.add_reaction("👍")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "👍" and reaction.message.id == confirm.id
        
        try:
            await bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏱️ Tiempo agotado. Operación cancelada.")
            return
    
    success, message = manager.stop_server()
    await ctx.send(message)

@bot.command(name="status")
async def status(ctx):
    """Muestra el estado del servidor"""
    status = manager.get_status()
    
    if not status["online"]:
        embed = discord.Embed(
            title="🔴 Servidor OFFLINE",
            color=0xff0000
        )
    else:
        embed = discord.Embed(
            title="🟢 Servidor ONLINE",
            description=f"**IP:** {SERVER_IP}",
            color=0x00ff00
        )
        embed.add_field(name="🖥️ Versión", value=status["version"], inline=True)
        embed.add_field(name="👥 Jugadores", value=f"{status['players']}/{status['max_players']}", inline=True)
        embed.add_field(name="⏱️ Latencia", value=f"{status['latency']:.2f} ms", inline=True)
        embed.add_field(name="📋 MOTD", value=status["motd"], inline=False)
        
        # Tiempo inactivo
        inactive_min = (time.time() - manager.last_player_time) // 60
        embed.add_field(name="⏳ Inactividad", value=f"{int(inactive_min)} minutos", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info(ctx):
    """Muestra los comandos disponibles"""
    embed = discord.Embed(
        title="Comandos disponibles",
        color=0x00ff00
    )
    embed.add_field(name="/abrir", value="Inicia el servidor", inline=False)
    embed.add_field(name="/cerrar", value="Apaga el servidor", inline=False)
    embed.add_field(name="/status", value="Muestra el estado del servidor", inline=False)
    embed.add_field(name="/info", value="Muestra esta ayuda", inline=False)
    await ctx.send(embed=embed)

bot.run(TOKEN)