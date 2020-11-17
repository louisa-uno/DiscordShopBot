import discord
import mysql.connector
import random
from config import mysql_config
from config import discord_config


client = discord.Client()

cart_database = mysql.connector.connect(user=mysql_config["user"],password=mysql_config["password"],host=mysql_config["host"],database=mysql_config["database"])
print(f"MySQL: Logged in as {cart_database.user}")
cart_cursor = cart_database.cursor()
cart_cursor.execute(f"CREATE TABLE IF NOT EXISTS `products` (`id` int NOT NULL AUTO_INCREMENT PRIMARY KEY, `enabled` varchar(255) DEFAULT NULL, `channel` varchar(255) DEFAULT NULL, `title` varchar(255) DEFAULT NULL, `price` varchar(255) DEFAULT NULL, `raw_price` varchar(255) DEFAULT NULL, `quantity` varchar(255) DEFAULT NULL, `image_url` varchar(255) DEFAULT NULL, `description` varchar(255) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")

@client.event
async def on_ready():
    print("Discord: Logged in as {0.user}".format(client))
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Anarchy Shop"))

@client.event
async def on_raw_reaction_add(raw_reaction):

    channel = await client.fetch_channel(raw_reaction.channel_id)
    message = await channel.fetch_message(raw_reaction.message_id)
    user = await client.fetch_user(raw_reaction.user_id)

    if user != client.user:
        cart_cursor.execute(f"SELECT EXISTS (SELECT * FROM products WHERE title = '{message.embeds[0].title}')")
        is_sell_message = cart_cursor.fetchall()
        if is_sell_message == [(1,)]:
            for reaction in message.reactions:
                if reaction.count >= 2:
                    database_user = f"{user}".replace("#","_")
                    if reaction.emoji == "🛒":
                        print(f"{user}: 🛒 Added to cart  ")
                        cart(database_user, 1, reaction)
                        await cart_message(database_user, reaction, user)
                    elif reaction.emoji == "❌":
                        print(f"{user}: ❌ Removed from cart")
                        cart(database_user, -1, reaction)
                        await cart_message(database_user, reaction, user)
                    await reaction.remove(user = user)
        if is_cart(message):
            for reaction in message.reactions:
                if reaction.count >= 2:
                    if reaction.emoji == "💰":
                        print(f"{user}: 💰  Gone to checkout  ")
                        database_user = f"{user}".replace("#","_")
                        await cart_ticket(database_user, reaction, user)
                    elif reaction.emoji == "🗑️":
                        print(f"{user}: 🗑️  Emptied cart")
                        database_user = f"{user}".replace("#","_")
                        await delete_cart(reaction, database_user, user)
        if is_order(message):
            for reaction in message.reactions:
                if reaction.count >= 2:
                    if reaction.emoji == "🗑️":
                        print(f"{user}: 🗑️  Cancelled checkout ")
                        await message.channel.delete()

async def cart_ticket(database_user, reaction, user):
    print(f"{user}") 
    cart_cursor.execute(f"SELECT EXISTS (SELECT * FROM {database_user})")
    cart_exists = cart_cursor.fetchall()
    if cart_exists == [(1,)]:
        cart_cursor.execute(f"SELECT * FROM {database_user}")
        products = cart_cursor.fetchall()
        embed = discord.Embed(title = discord_config["order_title"] , description = "" , color = discord.Colour.from_rgb(255, 0, 0))
        productnames = ""
        productquantity = ""
        productprices = ""
        total = 0
        for product in products:
            cart_cursor.execute(f"SELECT * FROM products WHERE id = '{product[0]}'")
            productinfo = cart_cursor.fetchall()[0]
            productnames = productnames + productinfo[3] + "\n "
            productquantity = productquantity + product[1] + "\n "
            productprices = productprices + productinfo[5] + "€" + "\n "
            total = total + (int(product[1]) * float(productinfo[5]))
        paypaltotal = round(total, 2) + (0.0249*total + 0.35)

        embed.add_field(name = "Name", value = f"{productnames}", inline = True)
        embed.add_field(name = "Count", value = f"{productquantity}", inline = True)
        embed.add_field(name = "Price", value = f"{productprices}", inline = True)
        embed.add_field(name = f"Total: {round(total, 2)}€ | With PayPal fees: {round(paypaltotal, 2)}€", value = f"(Maybe this message won't display well on mobile devices)", inline = True)

        await delete_dm(user)

        cart_cursor.execute(f"DROP TABLE IF EXISTS `{database_user}`")
        cart_database.commit()

        GUILD_ID = discord_config["guild_id"]
        guild = await client.fetch_guild(GUILD_ID)
        
        ticketchannel = await guild.create_text_channel(f"order-{database_user}")
        # await ticketchannel.edit(category=(777125722602995733))

        await ticketchannel.set_permissions(guild.default_role, read_messages=False, send_messages=False)
        await ticketchannel.set_permissions(user, read_messages=True, send_messages=True)
        await ticketchannel.set_permissions(discord.utils.get(guild.roles, name="Support"), read_messages=True, send_messages=True)

        await ticketchannel.send(embed=embed, content=f"<@{user.id}>")

async def delete_cart(reaction, database_user, user):
    cart_cursor.execute(f"DROP TABLE IF EXISTS {database_user}")
    cart_database.commit()
    await delete_dm(user)

def cart(database_user, cart_add_count, reaction):
    cart_cursor.execute(f"SELECT * FROM products WHERE title = '{reaction.message.embeds[0].title}'")
    productid = cart_cursor.fetchone()[0]

    cart_cursor.execute(f"CREATE TABLE IF NOT EXISTS `{database_user}` (`id` varchar(255) DEFAULT NULL, `quantity` varchar(255) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    cart_database.commit()
    
    cart_cursor.execute(f"SELECT EXISTS(SELECT * FROM {database_user} WHERE id ='{productid}')")
    cart_product_exists = cart_cursor.fetchall()
    if cart_product_exists == [(1,)]:
        cart_cursor.execute(f"SELECT * FROM {database_user} WHERE id ='{productid}'")
        cart = cart_cursor.fetchall()
        product = cart[0]
        cart_product_count = int(product[1])

        new_cart_product_count = cart_product_count + cart_add_count
        if new_cart_product_count <= 0:
            cart_cursor.execute(f"DELETE FROM {database_user} WHERE id = '{productid}'")
        else:
            cart_cursor.execute(f"UPDATE {database_user} SET quantity = '{new_cart_product_count}' WHERE id = '{productid}'")
        cart_database.commit()
        # print(f"{new_cart_product_count}x {productid} is in the cart")
    else:
        if cart_add_count > 0:
            cart_cursor.execute(f"INSERT INTO `{database_user}` (`id`, `quantity`) VALUES ('{productid}', '{cart_add_count}')")
            cart_database.commit()
            # print(f"Added {productid} to cart")

async def cart_message(database_user, reaction, user):
    cart_cursor.execute(f"SELECT EXISTS (SELECT * FROM {database_user})")
    cart_exists = cart_cursor.fetchall()
    if cart_exists == [(1,)]:
        cart_cursor.execute(f"SELECT * FROM {database_user}")
        products = cart_cursor.fetchall()
        embed = discord.Embed(title = discord_config["cart_title"] , description = "" , color = discord.Colour.from_rgb(255, 0, 0))
        productnames = ""
        productquantity = ""
        productprices = ""
        total = 0
        for product in products:
            cart_cursor.execute(f"SELECT * FROM products WHERE id = '{product[0]}'")
            productinfo = cart_cursor.fetchall()[0]
            productnames = productnames + productinfo[3] + "\n "
            productquantity = productquantity + product[1] + "\n "
            productprices = productprices + productinfo[5] + "€" + "\n "
            total = total + (int(product[1]) * float(productinfo[5]))

        embed.add_field(name = "Name", value = f"{productnames}", inline = True)
        embed.add_field(name = "Count", value = f"{productquantity}", inline = True)
        embed.add_field(name = "Price", value = f"{productprices}", inline = True)
        embed.add_field(name = f"Total: {round(total, 2)}€", value = f"Press 💰 to order, or press 🗑️ to clear the cart\n(Maybe this message won't display well on mobile devices)", inline = True)
        
        # await message.channel.send(embed=embed)

        DMChannel = await user.create_dm()
        cart_message = await DMChannel.history().find(lambda m: m.author.id == client.user.id)
        if cart_message == None:
            await DMChannel.send(embed=embed)
        else:
            await cart_message.edit(embed=embed)

        # await delete_dm(user)

async def delete_dm(user):
    DMChannel = await user.create_dm()
    async for message in DMChannel.history(limit=1000):
                if message.author.id == client.user.id:
                    await message.delete()

def is_cart(message):
    # print(message.embeds[0].title)
    return message.embeds[0].title == discord_config["cart_title"]

def is_order(message):
    # print(message.embeds[0].title)
    return message.embeds[0].title == discord_config["order_title"]

async def delete_messages(channel):
        deleted = await channel.purge(limit=100, check=None)
        await channel.send('Deleted {} message(s)'.format(len(deleted)))

@client.event
async def on_message(message):
    if message.author == client.user:
        cart_cursor.execute(f"SELECT EXISTS (SELECT * FROM products WHERE title = '{message.embeds[0].title}')")
        is_sell_message = cart_cursor.fetchall()
        if is_sell_message == [(1,)]:
            await message.add_reaction('🛒')
            await message.add_reaction('❌')
        if is_cart(message):
            await message.add_reaction('💰')
            await message.add_reaction('🗑️')
        if is_order(message):
            await message.add_reaction('🗑️')

    if message.author != client.user:
        role_names = [role.name for role in message.author.roles]
        if "Support" in role_names:
            if message.content.startswith("=add"):
                member = message.author
                # whois(message, member)
                cart_cursor.execute(f"select * from products WHERE channel = '{message.channel}' and enabled = 'true'")
                products = cart_cursor.fetchall()
                print(f"{member} created {cart_cursor.rowcount} products.")
                
                if products != []:
                    await message.channel.purge(limit=100, check=None)

                description = ""

                for product in products:
                    title = product[3]
                    price = product[4]
                    quantity = product[6]
                    url = product[7]
                    description = product[8]
                    if str(description) == "None":
                        description = "."
                
                    embed = discord.Embed(title = title , description = "" , color = discord.Colour.from_rgb(255, 0, 0))
                
                    embed.add_field(name = f"Price: {price}", value = description, inline = True)
                    embed.add_field(name = f"Quantity: {quantity}", value = ".", inline = True)
                    if str(url) != "None":
                        embed.set_image(url = url)

                    await message.channel.send(embed=embed)
client.run(discord_config["bot_token"])