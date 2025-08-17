import asyncio
from twitchio.ext import commands
import os
import configparser
import json
from pathlib import Path

# Load configuration from .config file
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', '.config'))

class ChatBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config['CHAT']['CHAT_TOKEN'],
            nick=config['CHAT']['BOT_USERNAME'],  # Explicit bot username
            prefix=config['CHAT']['PREFIX'],
            initial_channels=[config['CHAT']['CHANNEL']]  # Direct channel reference
        )
        self.counter_file = Path(__file__).parent / 'hellocounter.json'
        self.hello_count = self.load_counter()

    def load_counter(self):
        """Load counters from JSON file"""
        try:
            if self.counter_file.exists():
                with open(self.counter_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading counter: {e}")
        return {}

    def save_counter(self):
        """Save counters to JSON file"""
        try:
            with open(self.counter_file, 'w', encoding='utf-8') as f:
                json.dump(self.hello_count, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving counter: {e}")

    async def event_ready(self):
        print(f'🎉 Bot connected as {self.nick}')
        print(f'📊 Loaded counters: {len(self.hello_count)} users')

    async def event_message(self, message):
        if message.echo:
            return
        
        print(f'💬 #{message.channel.name} {message.author.name}: {message.content}')
        await self.handle_commands(message)

    @commands.command()
    async def hello(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        
        # Update count
        self.hello_count[user] = self.hello_count.get(user, 0) + 1
        self.save_counter()
        
        count = self.hello_count[user]
        response = (
            f"👋 Hello {user} 😄" 
        )
        await ctx.send(response)
        
    @commands.command()
    async def hellocount(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        count = self.hello_count.get(user, 0)
        await ctx.send(f"📊 @{user}, you were welcomed {count} times")

    @commands.command()
    async def tophello(self, ctx: commands.Context):
        """Show top 5 hello users"""
        if not self.hello_count:
            await ctx.send("No !hello counts yet! 😢")
            return
            
        top_users = sorted(self.hello_count.items(), key=lambda x: x[1], reverse=True)[:5]
        message = "🏆 Top !hello users: " + " | ".join(
            [f"{user}: {count}" for user, count in top_users]
        )
        await ctx.send(message)

    @commands.command()
    async def bot(self, ctx: commands.Context):
        """Bot info command"""
        await ctx.send("🤖 Hello! Commands available: !hello, !hellocount, !tophello and !bot.")
    
    @commands.command()
    async def test(self, ctx):
        try:
            await ctx.send("🔌 Teste de conexão!")
            print("✅ Mensagem de teste enviada")
        except Exception as e:
            print(f"❌ Falha no teste: {e}")

async def main():
    bot = ChatBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())