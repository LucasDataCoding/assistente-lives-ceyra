import asyncio
from twitchio.ext import commands
import os
import configparser
import json
import websockets

# Load configuration from .config file
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', '.config'))

class ChatBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config['CHAT']['CHAT_TOKEN'],
            nick=config['CHAT']['BOT_USERNAME'],
            prefix=config['CHAT']['PREFIX'],
            initial_channels=[config['CHAT']['CHANNEL']]  # Direct channel reference
        )

        self.websocket_clients = set()
        self.websocket_server = None

    async def start_websocket_server(self):
        """Inicia o servidor WebSocket para comunicação com Vue.js"""
        async def websocket_handler(websocket):
            self.websocket_clients.add(websocket)
            print(f"👤 Cliente Vue.js conectado. Total: {len(self.websocket_clients)}")
            
            try:
                # Manter a conexão aberta
                async for message in websocket:
                    # Você pode processar mensagens do Vue aqui se necessário
                    pass
            except websockets.exceptions.ConnectionClosed:
                print("👤 Cliente Vue.js desconectado")
            finally:
                self.websocket_clients.remove(websocket)
                print(f"👤 Cliente removido. Total: {len(self.websocket_clients)}")

        # Iniciar servidor WebSocket na porta 8765
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
        tasks = []
        
        for client in self.websocket_clients:
            try:
                tasks.append(client.send(message))
            except:
                # Remove clientes inválidos
                self.websocket_clients.discard(client)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def event_ready(self):
        print(f'🎉 Bot connected as {self.nick}')
        
        # Iniciar servidor WebSocket quando o bot estiver pronto
        await self.start_websocket_server()

    async def event_message(self, message):
        if message.echo:
            return
        
        # Enviar dados para o Vue.js
        data = {
            'channel': message.channel.name,
            'username': message.author.name,
            'message_color': message.author.color,
            'message': message.content,
            'timestamp': str(getattr(message, 'timestamp', '')),
            'type': 'chat_message'
        }
        
        # Broadcast para todos os clientes Vue
        await self.broadcast_to_vue(data)
        await self.handle_commands(message)

    @commands.command()
    async def bot(self, ctx: commands.Context):
        """Bot info commands"""
        await ctx.send("🤖 Hello, commands available: !bot, !github, !botcode and !chatcode")
    
    @commands.command()
    async def github(self, ctx: commands.Context):
        """GitHub link"""
        await ctx.send("https://github.com/LucasDataCoding")
        
    @commands.command()
    async def botcode(self, ctx: commands.Context):
        """Bot source code"""
        await ctx.send("https://github.com/LucasDataCoding/twitch-tv-chat-steroids")
    
    @commands.command()
    async def chatcode(self, ctx: commands.Context):
        """Bot source code"""
        await ctx.send("https://github.com/LucasDataCoding/twitch-chat-bash-theme")
    
async def main():
    bot = ChatBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Desligando bot...")
        await bot.close()
    except Exception as e:
        print(f"❌ Erro: {e}")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())