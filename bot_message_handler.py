import asyncio
from twitchio.ext import commands
import os
import configparser
import json
from pathlib import Path

# TODO
# Remove initial car
#   Add rule to only create one car per user
#   Create power ups to be picked on the ground
#       to allow players to fight eachother

# Load configuration from .config file
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', '.config'))

from unity_integration import spawn_car, move_car, spawned_cars

class ChatBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config['CHAT']['CHAT_TOKEN'],
            nick=config['CHAT']['BOT_USERNAME'],  # Explicit bot username
            prefix=config['CHAT']['PREFIX'],
            initial_channels=[config['CHAT']['CHANNEL']]  # Direct channel reference
        )

        self.counter_file = Path(__file__).parent / 'commands_counter.json'
        self.commands_count = self.load_counter()

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
                json.dump(self.commands_count, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving counter: {e}")

    async def event_ready(self):
        print(f'🎉 Bot connected as {self.nick}')
        print(f'📊 Loaded counters: {len(self.commands_count)} users')

    async def event_message(self, message):
        if message.echo:
            return
        
        print(f'💬 #{message.channel.name} {message.author.name}: {message.content}')
        await self.handle_commands(message)

    def get_user_name(self, ctx):
        return ctx.author.name.lower()

    def get_count_command(self, ctx, command):
        user_name = self.get_user_name(ctx)

        if(self.commands_count.get(command, None) == None):
            return 0

        return self.commands_count[command].get(user_name, 0) 

    def set_count_command(self, ctx, command):
        user_name = self.get_user_name(ctx)

        if(self.commands_count.get(command, None) == None):
            self.commands_count[command] = {}

        self.commands_count[command][user_name] = self.get_count_command(ctx, command) + 1
        self.save_counter()
        
    
    async def topcommand(self, ctx: commands.Context, command):
        if not self.commands_count:
            await ctx.send(f"No !{command} counts yet! 😢")
            return
            
        top_users = sorted(self.commands_count.get(command, {}).items(), key=lambda x: x[1], reverse=True)[:5]
        message = f"🏆 Top !{command} senders: " + " | ".join(
            [f"{user}: {count}" for user, count in top_users]
        )
        await ctx.send(message)

    @commands.command()
    async def bot(self, ctx: commands.Context):
        # Bot info commands
        await ctx.send("🤖 Hello! Commands available: !hello, !hellocount, !tophello, !bot, !spawn and !spawncount.")
    
    @commands.command()
    async def hello(self, ctx: commands.Context):
        user = self.get_user_name(ctx)
        self.set_count_command(ctx, 'hello')
        
        response = (
            f"👋 Hello {user} 😄" 
        )

        await ctx.send(response)
        
    @commands.command()
    async def hellocount(self, ctx: commands.Context):
        user = self.get_user_name(ctx)
        count = self.get_count_command(ctx, 'hello')
        await ctx.send(f"📊 @{user}, you were welcomed {count} times")

    @commands.command()
    async def tophello(self, ctx: commands.Context):
        await self.topcommand(ctx, 'hello')

    @commands.command()
    async def spawn(self, ctx):
        try:
            spawn_car(ctx.author.name.lower())
        
            self.set_count_command(ctx, 'spawn')
        
            print("✅ Mensagem de teste enviada")
        except Exception as e:
            print(f"❌ Falha no teste: {e}")

    @commands.command()
    async def forward(self, ctx):
        player_name = ctx.author.name.lower()

        try:
            if player_name in spawned_cars.values():
                car_id = next(key for key, value in spawned_cars.items() if value == player_name)
                print(f"Found user Car: {car_id}")
                move_car(car_id, "forward", 5)  # Usa o ID do carro, não o nome!
            else:
                print(f"❌ {player_name} não tem um carro spawnado.")
        except Exception as e:
            print(f"❌ Fail on move forward: {e}")

    @commands.command()
    async def back(self, ctx):
        player_name = ctx.author.name.lower()
        
        try:
            if player_name in spawned_cars.values():
                car_id = next(key for key, value in spawned_cars.items() if value == player_name)
                print(f"Found user Car: {car_id}")
                move_car(car_id, "back", 5)  # Movimento de ré por 5 segundos
            else:
                print(f"❌ {player_name} não tem um carro spawnado.")
        except Exception as e:
            print(f"❌ Fail on move back: {e}")

    @commands.command()
    async def left(self, ctx):
        player_name = ctx.author.name.lower()
        
        try:
            if player_name in spawned_cars.values():
                car_id = next(key for key, value in spawned_cars.items() if value == player_name)
                print(f"Found user Car: {car_id}")
                move_car(car_id, "left", 3)  # Virar à esquerda por 3 segundos
            else:
                print(f"❌ {player_name} não tem um carro spawnado.")
        except Exception as e:
            print(f"❌ Fail on turn left: {e}")

    @commands.command()
    async def right(self, ctx):
        player_name = ctx.author.name.lower()
        
        try:
            if player_name in spawned_cars.values():
                car_id = next(key for key, value in spawned_cars.items() if value == player_name)
                print(f"Found user Car: {car_id}")
                move_car(car_id, "right", 3)  # Virar à direita por 3 segundos
            else:
                print(f"❌ {player_name} não tem um carro spawnado.")
        except Exception as e:
            print(f"❌ Fail on turn right: {e}")

    @commands.command()
    async def spawncount(self, ctx: commands.Context):
        user = self.get_user_name(ctx)
        count = self.get_count_command(ctx, 'spawn')
        await ctx.send(f"📊 @{user}, you spawned {count} times")

    @commands.command()
    async def topspawn(self, ctx: commands.Context):
        await self.topcommand(ctx, 'spawn')

async def main():
    bot = ChatBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())