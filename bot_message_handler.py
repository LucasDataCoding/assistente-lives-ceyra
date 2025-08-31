import asyncio
from twitchio.ext import commands
import os
import configparser
import json
import websockets
from flask import Flask, send_from_directory
import threading

# Load configuration from .config file
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', '.config'))
app = Flask(__name__)

# Configuração para servir arquivos estáticos
app.static_folder = 'dist/assets'
app.static_url_path = '/assets'

@app.route('/')
def serve_vue_app():
    return send_from_directory('dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Serve outros arquivos estáticos (JS, CSS, imagens)
    if os.path.exists(f'dist/{path}') and os.path.isfile(f'dist/{path}'):
        return send_from_directory('dist', path)
    # Para rotas do Vue Router (HTML5 History Mode)
    return send_from_directory('dist', 'index.html')

def run_flask():
    """Executa o servidor Flask em uma thread separada"""
    print("🚀 Iniciando servidor Flask na porta 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

class ChatBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config['CHAT']['CHAT_TOKEN'],
            nick=config['CHAT']['BOT_USERNAME'],
            prefix=config['CHAT']['PREFIX'],
            initial_channels=[config['CHAT']['CHANNEL']]
        )
        self.websocket_clients = set()
        self.websocket_server = None

    async def start_websocket_server(self):
        """Inicia o servidor WebSocket para comunicação com Vue.js"""
        async def websocket_handler(websocket):
            self.websocket_clients.add(websocket)
            print(f"👤 Cliente Vue.js conectado. Total: {len(self.websocket_clients)}")
            
            try:
                async for message in websocket:
                    # Processar mensagens do Vue aqui se necessário
                    pass
            except websockets.exceptions.ConnectionClosed:
                print("👤 Cliente Vue.js desconectado")
            finally:
                self.websocket_clients.remove(websocket)

        self.websocket_server = await websockets.serve(
            websocket_handler, 
            "localhost", 
            8765
        )
        print("🚀 Servidor WebSocket iniciado em ws://localhost:8765")

    async def broadcast_to_vue(self, data):
        """Envia dados para todos os clientes Vue.js conectados"""
        if not self.websocket_clients:
            return

        message = json.dumps(data)
        for client in self.websocket_clients.copy():
            try:
                await client.send(message)
            except:
                self.websocket_clients.discard(client)

    async def event_ready(self):
        print(f'🎉 Bot connected as {self.nick}')
        await self.start_websocket_server()

    async def event_message(self, message):
        if message.echo:
            return
        
        data = {
            'channel': message.channel.name,
            'username': message.author.name,
            'message_color': message.author.color,
            'message': message.content,
            'timestamp': str(getattr(message, 'timestamp', '')),
            'type': 'chat_message'
        }
        
        await self.broadcast_to_vue(data)
        await self.handle_commands(message)

    @commands.command()
    async def bot(self, ctx: commands.Context):
        await ctx.send("🤖 Hello, commands available: !bot, !github, !botcode and !chatcode")
    
    @commands.command()
    async def github(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding")
        
    @commands.command()
    async def botcode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")
    
    @commands.command()
    async def youtube(self, ctx: commands.Context):
        await ctx.send("https://www.youtube.com/@lucas-data-code")

    @commands.command()
    async def chatcode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")

async def main():
    # Iniciar Flask em uma thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Iniciar o bot Twitch
    bot = ChatBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Desligando bot...")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(main())