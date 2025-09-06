import asyncio
from twitchio.ext import commands
import os
import configparser
import json
import websockets
from flask import Flask, send_from_directory, request
import threading
import mimetypes

# Load configuration from .config file
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', '.config'))
app = Flask(__name__)

# Configura MIME types manualmente
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('image/svg+xml', '.svg')

@app.route('/')
def serve_vue_app():
    return send_from_directory('dist', 'index.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve arquivos da pasta assets com MIME types corretos"""
    response = send_from_directory('dist/assets', path)
    
    # Define MIME types corretos
    if path.endswith('.js'):
        response.headers.set('Content-Type', 'application/javascript')
    elif path.endswith('.css'):
        response.headers.set('Content-Type', 'text/css')
    elif path.endswith('.json'):
        response.headers.set('Content-Type', 'application/json')
    
    return response

@app.route('/<path:path>')
def serve_static(path):
    """Serve outros arquivos estáticos"""
    static_extensions = ['.js', '.css', '.json', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.woff', '.woff2', '.ttf', '.eot']
    
    # Verifica se é um arquivo estático
    if any(path.endswith(ext) for ext in static_extensions):
        if os.path.exists(f'dist/{path}'):
            response = send_from_directory('dist', path)
            
            # Define MIME types
            if path.endswith('.js'):
                response.headers.set('Content-Type', 'application/javascript')
            elif path.endswith('.css'):
                response.headers.set('Content-Type', 'text/css')
            elif path.endswith('.json'):
                response.headers.set('Content-Type', 'application/json')
            elif path.endswith('.ico'):
                response.headers.set('Content-Type', 'image/x-icon')
            
            return response 
    
    # Para todas as outras rotas, serve index.html (Vue Router)
    return send_from_directory('dist', 'index.html')

def run_flask():
    """Executa o servidor Flask em uma thread separada"""
    print("🚀 Iniciando servidor Flask na porta 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

class ChatBot(commands.Bot):
    def __init__(self):
        # Use get() com fallback para evitar erros se o arquivo não existir
        super().__init__(
            token=config.get('CHAT', 'CHAT_TOKEN', fallback='oauth:YOUR_BOT_TOKEN_HERE'),
            nick=config.get('CHAT', 'BOT_USERNAME', fallback='YOUR_BOT_NAME_HERE'),
            prefix=config.get('CHAT', 'PREFIX', fallback='!'),
            initial_channels=[config.get('CHAT', 'CHANNEL', fallback='YOUR_CHANNEL_NAME_LOWERCASE_HERE')]
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
        await ctx.send("🤖 Comandos disponíveis: !bot, !github, !botcode and !chatcode, !chatvuecode")
    
    @commands.command()
    async def github(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding")
        
    @commands.command()
    async def botcode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")
    
    @commands.command()
    async def youtube(self, ctx: commands.Context):
        await ctx.send("https://www.youtube.com/@lucas-data-coding")

    @commands.command()
    async def chatcode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")
    
    @commands.command()
    async def chatvuecode(self, ctx: commands.Context):
        await ctx.send("https://github.com/LucasDataCoding/twitch-chat-bash-theme")

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