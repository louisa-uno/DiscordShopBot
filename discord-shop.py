import discord
import mysql.connector
import time
import json
import requests
import validators

with open("config.json") as f:
    config = json.load(f)
    config_mysql = config["mysql"]
    config_discord = config["discord"]

client = discord.Client()

cart_database = test_mysql = mysql.connector.connect(
    user=config_mysql["user"],
    password=config_mysql["password"],
    host=config_mysql["host"],
    port=config_mysql["port"],
    database=config_mysql["database"])

print(f"MySQL: Logged in as {cart_database.user}")
cart_cursor = cart_database.cursor(buffered=False)
cart_cursor.execute(
    f"CREATE TABLE IF NOT EXISTS `items` (`id` int NOT NULL AUTO_INCREMENT PRIMARY KEY, `name` varchar(256) DEFAULT NULL, `description` varchar(1024) DEFAULT NULL, `url` varchar(1024) DEFAULT NULL, `price` varchar(255) DEFAULT NULL, `quantity` varchar(255) DEFAULT NULL, `channel_id` varchar(255) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
)
cart_database.commit()


@client.event
async def on_ready():
    print("Discord: Logged in as {0.user}".format(client))
    await client.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing, name="Anarchy Shop"))
    # Creates Support role if it doesn't exists
    for guild in client.guilds:
        roleExists = False
        for role in guild.roles:
            if "Support" in role.name:
                roleExists = True
        if roleExists == False:
            await guild.create_role(name="Support",
                                    reason="Is necessary for DiscordShopBot")


@client.event
async def on_raw_reaction_add(raw_reaction):

    channel = await client.fetch_channel(raw_reaction.channel_id)
    message = await channel.fetch_message(raw_reaction.message_id)
    user = await client.fetch_user(raw_reaction.user_id)

    if user != client.user:
        cart_cursor.execute(
            f"SELECT EXISTS (SELECT * FROM items WHERE name = '{message.embeds[0].title}')"
        )
        is_sell_message = cart_cursor.fetchall()
        if is_sell_message == [(1, )]:
            for reaction in message.reactions:
                await reaction.remove(user=user)
                if reaction.count >= 2:
                    database_user = f"{user}".replace("#", "_")
                    if reaction.emoji == "🛒":
                        print(f"{user}: 🛒 Added to cart")
                        cart(database_user, 1, reaction)
                        await cart_message(database_user, reaction, user)
                    elif reaction.emoji == "❌":
                        print(f"{user}: ❌ Removed from cart")
                        cart(database_user, -1, reaction)
                        await cart_message(database_user, reaction, user)
                elif reaction.emoji == "✏️":
                    await edit_item(reaction, user)
                elif reaction.emoji == "🗑️":
                    await delete_item(reaction, user)
        elif is_cart(message):
            for reaction in message.reactions:
                if reaction.count >= 2:
                    if reaction.emoji == "💰":
                        print(f"{user}: 💰  Gone to checkout")
                        database_user = f"{user}".replace("#", "_")
                        await cart_ticket(database_user, reaction, user)
                    elif reaction.emoji == "🗑️":
                        print(f"{user}: 🗑️  Emptied cart")
                        database_user = f"{user}".replace("#", "_")
                        await delete_cart(reaction, database_user, user)
        elif is_order(message):
            for reaction in message.reactions:
                if reaction.count >= 2:
                    if reaction.emoji == "🗑️":
                        print(f"{user}: 🗑️  Cancelled checkout")
                        await message.channel.delete()


async def delete_item(reaction, user):
    GUILD_ID = config_discord["guild_id"]
    guild = await client.fetch_guild(GUILD_ID)
    guild_member = await guild.fetch_member(user.id)

    role_names = [role.name for role in guild_member.roles]
    if not "Support" in role_names:
        return

    item_name = reaction.message.embeds[0].title

    print(f"{user}: 🗑️  {item_name}")

    edit_item_channel = await guild.create_text_channel(f"delete-{item_name}")

    await edit_item_channel.set_permissions(guild.default_role,
                                            read_messages=False,
                                            send_messages=False)
    await edit_item_channel.set_permissions(user,
                                            read_messages=True,
                                            send_messages=True)
    await edit_item_channel.set_permissions(discord.utils.get(guild.roles,
                                                              name="Support"),
                                            read_messages=True,
                                            send_messages=True)

    def check(m):
        return m.channel == edit_item_channel and m.author == guild_member

    cart_cursor.execute(f"SELECT * FROM items WHERE name = '{item_name}'")
    productinfo = cart_cursor.fetchall()[0]
    item_id = productinfo[0]
    item_name = productinfo[1]
    item_description = productinfo[2]
    item_image = productinfo[3]
    item_price = productinfo[4]
    item_quantity_database = productinfo[5]
    if str(item_quantity_database) == "-1":
        item_quantity = "Unlimited"
    else:
        item_quantity = item_quantity_database

    while True:
        embed = discord.Embed(title=f"Item preview:\n\n{item_name}",
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))
        embed.add_field(name=f"Price: {item_price}€",
                        value=item_description,
                        inline=True)
        embed.add_field(name=f"Quantity: {item_quantity}",
                        value=".",
                        inline=True)
        if str(item_image) != "." and "None":
            embed.set_image(url=item_image)
        await edit_item_channel.send(embed=embed, content="")

        embed = discord.Embed(title="Are you sure to delete the item?",
                              description="Answer with yes or no",
                              color=discord.Colour.from_rgb(255, 0, 0))
        await edit_item_channel.send(embed=embed, content=f"<@{user.id}>")

        edit_item_menu_message = await client.wait_for('message', check=check)
        edit_item_menu = edit_item_menu_message.content

        if edit_item_menu == "yes":
            embed = discord.Embed(title="Deleting ...",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
            time.sleep(2)

            cart_cursor.execute(f"DELETE FROM items WHERE id = '{item_id}'")
            cart_database.commit()

            await reaction.message.delete()
            await edit_item_channel.delete()
            break
        elif edit_item_menu == "no":
            embed = discord.Embed(title="Cancelling ...",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
            time.sleep(2)
            await edit_item_channel.delete()
            break


async def edit_item(reaction, user):
    GUILD_ID = config_discord["guild_id"]
    guild = await client.fetch_guild(GUILD_ID)
    guild_member = await guild.fetch_member(user.id)

    role_names = [role.name for role in guild_member.roles]
    if not "Support" in role_names:
        return

    item_name = reaction.message.embeds[0].title

    print(f"{user}: ✏️  {item_name}")

    edit_item_channel = await guild.create_text_channel(f"edit-{item_name}")

    await edit_item_channel.set_permissions(guild.default_role,
                                            read_messages=False,
                                            send_messages=False)
    await edit_item_channel.set_permissions(user,
                                            read_messages=True,
                                            send_messages=True)
    await edit_item_channel.set_permissions(discord.utils.get(guild.roles,
                                                              name="Support"),
                                            read_messages=True,
                                            send_messages=True)

    def check(m):
        return m.channel == edit_item_channel and m.author == guild_member

    cart_cursor.execute(f"SELECT * FROM items WHERE name = '{item_name}'")
    productinfo = cart_cursor.fetchall()[0]
    item_id = productinfo[0]
    item_name = productinfo[1]
    item_description = productinfo[2]
    item_image = productinfo[3]
    item_price = productinfo[4]
    item_quantity_database = productinfo[5]
    if str(item_quantity_database) == "-1":
        item_quantity = "Unlimited"
    else:
        item_quantity = item_quantity_database

    while True:
        embed = discord.Embed(title=f"Item preview:\n\n{item_name}",
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))
        embed.add_field(name=f"Price: {item_price}€",
                        value=item_description,
                        inline=True)
        embed.add_field(name=f"Quantity: {item_quantity}",
                        value=".",
                        inline=True)
        if str(item_image) != "." and "None":
            embed.set_image(url=item_image)
        await edit_item_channel.send(embed=embed, content="")

        embed = discord.Embed(title="How to edit:",
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))
        embed.add_field(name=f"Edit name", value="Usage: =name", inline=True)
        embed.add_field(name=f"Edit description",
                        value="Usage: =description",
                        inline=True)
        embed.add_field(name=f"Edit image", value="Usage: =image", inline=True)
        embed.add_field(name=f"Edit price", value="Usage: =price", inline=True)
        embed.add_field(name=f"Edit quantity",
                        value="Usage: =quantity",
                        inline=True)
        embed.add_field(name=f"Cancel editing",
                        value="Usage: =cancel",
                        inline=True)
        embed.add_field(name=f"Save changes",
                        value="Usage: =save",
                        inline=True)
        #embed.add_field(name = f"DISABLED: Edit category", value = "Usage: =category", inline = True)
        await edit_item_channel.send(embed=embed, content=f"<@{user.id}>")

        edit_item_menu_message = await client.wait_for('message', check=check)
        edit_item_menu = edit_item_menu_message.content

        if edit_item_menu == "=name":
            while True:
                embed = discord.Embed(title="What should be the item name?",
                                      description="",
                                      color=discord.Colour.from_rgb(255, 0, 0))
                embed.add_field(name=f"Current name:",
                                value=f"```{item_name}```",
                                inline=True)
                await edit_item_channel.send(embed=embed)
                item_name_message = await client.wait_for('message',
                                                          check=check)
                new_item_name = item_name_message.content
                if new_item_name != item_name:
                    cart_cursor.execute(
                        f"SELECT * FROM items WHERE name = '{new_item_name}'")
                    if cart_cursor.fetchall() != []:
                        embed = discord.Embed(
                            title="You can't have 2 items with the same name.",
                            description=
                            "Just delete the old one or choose another name to proceed.",
                            color=discord.Colour.from_rgb(255, 0, 0))
                        await edit_item_channel.send(embed=embed)
                    else:
                        if len(new_item_name) > 256:
                            embed = discord.Embed(
                                title="The maximum length is 256 characters.",
                                description="",
                                color=discord.Colour.from_rgb(255, 0, 0))
                            await edit_item_channel.send(embed=embed)
                        else:
                            item_name = new_item_name
                            break
                else:
                    break
            embed = discord.Embed(title="Name set to:",
                                  description=f"```{item_name}```",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
        elif edit_item_menu == "=description":
            while True:
                embed = discord.Embed(
                    title="What should be the item description?",
                    description="Enter . for no description.",
                    color=discord.Colour.from_rgb(255, 0, 0))
                embed.add_field(name=f"Current description:",
                                value=f"```{item_description}```",
                                inline=True)
                await edit_item_channel.send(embed=embed)
                item_description_message = await client.wait_for('message',
                                                                 check=check)
                new_item_description = item_description_message.content
                if len(new_item_description) > 1024:
                    embed = discord.Embed(
                        title="The maximum length is 1024 characters.",
                        description="",
                        color=discord.Colour.from_rgb(255, 0, 0))
                    await edit_item_channel.send(embed=embed)
                else:
                    item_description = new_item_description
                    break
            embed = discord.Embed(title="Description set to:",
                                  description=f"```{item_description}```",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
        elif edit_item_menu == "=image":
            while True:
                embed = discord.Embed(
                    title="What should be the new item image?",
                    description=
                    "Please enter public URL to the image \nValid Files are png, jpg or gif. \n Enter a . for no image.",
                    color=discord.Colour.from_rgb(255, 0, 0))
                embed.add_field(name=f"Current image:",
                                value=f"```{item_image}```",
                                inline=True)
                if str(item_image) != "." and "None":
                    embed.set_image(url=item_image)
                await edit_item_channel.send(embed=embed)
                item_image_message = await client.wait_for('message',
                                                           check=check)
                new_item_image = item_image_message.content
                if str(new_item_image) == ".":
                    item_image = new_item_image
                    break
                elif validators.url(new_item_image) == True:
                    if len(new_item_image) > 1024:
                        embed = discord.Embed(
                            title="The maximum length is 1024 characters.",
                            description="",
                            color=discord.Colour.from_rgb(255, 0, 0))
                        await edit_item_channel.send(embed=embed)
                    else:
                        if is_url_image(new_item_image) == True:
                            item_image = new_item_image
                            break
                        else:
                            embed = discord.Embed(
                                title=
                                "The image url isn't the right file format.",
                                description="",
                                color=discord.Colour.from_rgb(255, 0, 0))
                            await edit_item_channel.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="The image url is not public or not existing.",
                        description="",
                        color=discord.Colour.from_rgb(255, 0, 0))
                    await edit_item_channel.send(embed=embed)
            embed = discord.Embed(title="Image set to:",
                                  description=f"```{item_image}```",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
        elif edit_item_menu == "=price":
            while True:
                embed = discord.Embed(
                    title="What should be the item price?",
                    description="Please enter the price like this: 0.1",
                    color=discord.Colour.from_rgb(255, 0, 0))
                embed.add_field(name=f"Current price:",
                                value=f"```{item_price}```",
                                inline=True)
                await edit_item_channel.send(embed=embed)
                item_price_message = await client.wait_for('message',
                                                           check=check)
                new_item_price = item_price_message.content
                try:
                    new_item_price = round(float(new_item_price), 2)
                    if new_item_price > 0:
                        item_price = new_item_price
                        break
                    elif new_item_price == 0:
                        embed = discord.Embed(
                            title="The item price can't be zero.",
                            description="",
                            color=discord.Colour.from_rgb(255, 0, 0))
                        await edit_item_channel.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            title="The item price can't be below zero",
                            description="",
                            color=discord.Colour.from_rgb(255, 0, 0))
                        await edit_item_channel.send(embed=embed)
                except ValueError:
                    embed = discord.Embed(title="Please enter a valid price.",
                                          description="",
                                          color=discord.Colour.from_rgb(
                                              255, 0, 0))
                    await edit_item_channel.send(embed=embed)
            embed = discord.Embed(title="Price set to:",
                                  description=f"```{item_price}```",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
        elif edit_item_menu == "=quantity":
            while True:
                embed = discord.Embed(
                    title="What should be the item quantity?",
                    description="0 means out of stock \n-1 means unlimited",
                    color=discord.Colour.from_rgb(255, 0, 0))
                embed.add_field(name=f"Current quantity:",
                                value=f"```{item_quantity}```",
                                inline=True)
                await edit_item_channel.send(embed=embed)
                item_quantity_message = await client.wait_for('message',
                                                              check=check)
                new_item_quantity_database = item_quantity_message.content
                try:
                    new_item_quantity_database = int(
                        new_item_quantity_database)
                    if new_item_quantity_database > -1:
                        item_quantity = new_item_quantity_database
                        item_quantity_database = new_item_quantity_database
                        break
                    elif new_item_quantity_database == -1:
                        item_quantity = "Unlimited"
                        item_quantity_database = new_item_quantity_database
                        break
                    else:
                        embed = discord.Embed(
                            title=
                            "The item quantity can't be below -1(Unlimited).",
                            description="",
                            color=discord.Colour.from_rgb(255, 0, 0))
                        await edit_item_channel.send(embed=embed)
                except ValueError:
                    embed = discord.Embed(
                        title="Please enter a valid quantity.",
                        description="",
                        color=discord.Colour.from_rgb(255, 0, 0))
                    await edit_item_channel.send(embed=embed)
            embed = discord.Embed(title="Quantity set to:",
                                  description=f"```{item_quantity}```",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
        elif edit_item_menu == "=save":
            embed = discord.Embed(title="Saving ...",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
            time.sleep(2)
            await edit_item_channel.delete()

            embed = discord.Embed(title=item_name,
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            embed.add_field(name=f"Price: {item_price}€",
                            value=item_description,
                            inline=True)
            embed.add_field(name=f"Quantity: {item_quantity}",
                            value=".",
                            inline=True)
            if str(item_image) != "." and "None":
                embed.set_image(url=item_image)
            await reaction.message.edit(embed=embed)

            cart_cursor.execute(
                f"UPDATE items SET name = '{item_name}', description = '{item_description}', url = '{item_image}', price = '{item_price}', quantity = '{item_quantity_database}' WHERE id = '{item_id}'"
            )
            cart_database.commit()
            break
        elif edit_item_menu == "=cancel":
            embed = discord.Embed(title="Cancelling ...",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)
            await edit_item_channel.delete()
            break
        else:
            embed = discord.Embed(title="Invalid Command",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await edit_item_channel.send(embed=embed)


async def cart_ticket(database_user, reaction, user):
    print(f"{user}")
    cart_cursor.execute(f"SELECT EXISTS (SELECT * FROM {database_user})")
    cart_exists = cart_cursor.fetchall()
    if cart_exists == [(1, )]:
        cart_cursor.execute(f"SELECT * FROM {database_user}")
        products = cart_cursor.fetchall()
        embed = discord.Embed(title=config_discord["messages"]["order_title"],
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))
        productnames = ""
        productquantity = ""
        productprices = ""
        total = 0
        for product in products:
            cart_cursor.execute(
                f"SELECT * FROM items WHERE id = '{product[0]}'")
            productinfo = cart_cursor.fetchall()[0]
            productnames = productnames + productinfo[1] + "\n "
            productquantity = productquantity + product[1] + "\n "
            productprices = productprices + productinfo[4] + "€" + "\n "
            total = total + (int(product[1]) * float(productinfo[4]))
        paypaltotal = round(total, 2) + (0.0249 * total + 0.35)

        embed.add_field(name="Name", value=f"{productnames}", inline=True)
        embed.add_field(name="Count", value=f"{productquantity}", inline=True)
        embed.add_field(name="Price", value=f"{productprices}", inline=True)
        embed.add_field(
            name=
            f"Total: {round(total, 2)}€ | With PayPal fees: {round(paypaltotal, 2)}€",
            value=f"(Maybe this message won't display well on mobile devices)",
            inline=True)

        await delete_dm(user)

        cart_cursor.execute(f"DROP TABLE IF EXISTS `{database_user}`")
        cart_database.commit()

        GUILD_ID = config_discord["guild_id"]
        guild = await client.fetch_guild(GUILD_ID)

        ticketchannel = await guild.create_text_channel(
            f"order-{database_user}")

        await ticketchannel.set_permissions(guild.default_role,
                                            read_messages=False,
                                            send_messages=False)
        await ticketchannel.set_permissions(user,
                                            read_messages=True,
                                            send_messages=True)
        await ticketchannel.set_permissions(discord.utils.get(guild.roles,
                                                              name="Support"),
                                            read_messages=True,
                                            send_messages=True)

        sent_ticket_message = await ticketchannel.send(embed=embed,
                                                       content=f"<@{user.id}>")
        await sent_ticket_message.add_reaction('🗑️')


async def delete_cart(reaction, database_user, user):
    cart_cursor.execute(f"DROP TABLE IF EXISTS {database_user}")
    cart_database.commit()
    await delete_dm(user)


def cart(database_user, cart_add_count, reaction):
    cart_cursor.execute(
        f"SELECT `id`, `quantity` FROM items WHERE name = '{reaction.message.embeds[0].title}'"
    )
    productid = cart_cursor.fetchone()[0]

    cart_cursor.execute(
        f"CREATE TABLE IF NOT EXISTS `{database_user}` (`id` varchar(255) DEFAULT NULL, `quantity` varchar(255) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    cart_database.commit()
    cart_cursor.execute(
        f"SELECT * FROM {database_user} WHERE id ='{productid}'")
    cart = cart_cursor.fetchall()
    if cart == []:
        cart_cursor.execute(
            f"INSERT INTO `{database_user}` (`id`, `quantity`) VALUES ('{productid}', '{cart_add_count}')"
        )
        cart_database.commit()
    else:
        product = cart[0]
        cart_product_count = int(product[1])
        new_cart_product_count = cart_product_count + cart_add_count
        if new_cart_product_count <= 0:
            cart_cursor.execute(
                f"DELETE FROM {database_user} WHERE id = '{productid}'")
        else:
            cart_cursor.execute(
                f"UPDATE {database_user} SET quantity = '{new_cart_product_count}' WHERE id = '{productid}'"
            )
        cart_database.commit()


async def cart_message(database_user, reaction, user):
    cart_cursor.execute(f"SELECT EXISTS (SELECT * FROM {database_user})")
    cart_exists = cart_cursor.fetchall()
    if cart_exists == [(1, )]:
        cart_cursor.execute(f"SELECT * FROM {database_user}")
        products = cart_cursor.fetchall()
        embed = discord.Embed(title=config_discord["messages"]["cart_title"],
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))
        productnames = ""
        productquantity = ""
        productprices = ""
        total = 0
        for product in products:
            cart_cursor.execute(
                f"SELECT * FROM items WHERE id = '{product[0]}'")
            productinfo = cart_cursor.fetchall()[0]
            productnames = productnames + productinfo[1] + "\n "
            productquantity = productquantity + product[1] + "\n "
            productprices = productprices + productinfo[4] + "€" + "\n "
            total = total + (int(product[1]) * float(productinfo[4]))

        embed.add_field(name="Name", value=f"{productnames}", inline=True)
        embed.add_field(name="Count", value=f"{productquantity}", inline=True)
        embed.add_field(name="Price", value=f"{productprices}", inline=True)
        embed.add_field(
            name=f"Total: {round(total, 2)}€",
            value=
            f"Press 💰 to order, or press 🗑️ to clear the cart\n(Maybe this message won't display well on mobile devices)\nDeveloper: Louis_45#0553 | [GitHub](https://github.com/Luois45)",
            inline=True)

        DMChannel = await user.create_dm()
        cart_message = await DMChannel.history().find(
            lambda m: m.author.id == client.user.id)
        if cart_message == None:
            sent_cart_message = await DMChannel.send(embed=embed)
            await sent_cart_message.add_reaction('💰')
            await sent_cart_message.add_reaction('🗑️')
        else:
            await cart_message.edit(embed=embed)


async def delete_dm(user):
    DMChannel = await user.create_dm()
    async for message in DMChannel.history(limit=1000):
        if message.author.id == client.user.id:
            await message.delete()


def is_cart(message):
    return message.embeds[0].title == config_discord["messages"]["cart_title"]


def is_order(message):
    return message.embeds[0].title == config_discord["messages"]["order_title"]


async def delete_messages(channel):
    deleted = await channel.purge(limit=10000, check=None)
    await channel.send('Deleted {} message(s)'.format(len(deleted)))


async def help_command(message):
    embed = discord.Embed(title="Command Help",
                          description="",
                          color=discord.Colour.from_rgb(255, 0, 0))

    embed.add_field(name=f"Command Help", value="Usage: =help", inline=True)
    embed.add_field(name=f"Delete all messages in a channel",
                    value="Usage: =clear",
                    inline=True)
    embed.add_field(name=f"Create a shop category",
                    value="Usage: =addcategory",
                    inline=True)
    embed.add_field(name=f"Create a shop channel",
                    value="Usage: =addchannel",
                    inline=True)
    embed.add_field(name=f"Create a item",
                    value="Usage: =additem",
                    inline=True)
    # embed.add_field(name = f"DISABLED: Recreate all items", value = "Usage: =add", inline = True)
    embed.add_field(name=f"React with a ✏️ to a item to edit it.",
                    value="Usage: Reaction ✏️",
                    inline=True)
    embed.add_field(
        name=f"Developer",
        value=
        "Louis_45#0553 | [GitHub](https://github.com/Luois45)\ndiscord-shop@louis45.de",
        inline=True)

    await message.channel.send(embed=embed)


async def addcategory_command(message):
    GUILD_ID = config_discord["guild_id"]
    guild = await client.fetch_guild(GUILD_ID)
    channel = message.channel
    author = message.author

    embed = discord.Embed(title="What should be the category name?",
                          description="",
                          color=discord.Colour.from_rgb(255, 0, 0))
    await message.channel.send(embed=embed)

    def check(m):
        return m.channel == channel and m.author == author

    category = await client.wait_for('message', check=check)
    category_name = category.content

    embed = discord.Embed(title=f"Created the category {category_name}",
                          description="",
                          color=discord.Colour.from_rgb(255, 0, 0))
    await message.channel.send(embed=embed)
    created_category = await guild.create_category(category_name)

    await created_category.set_permissions(guild.default_role,
                                           read_messages=True,
                                           send_messages=False)
    await created_category.set_permissions(discord.utils.get(guild.roles,
                                                             name="Support"),
                                           read_messages=True,
                                           send_messages=True)


async def addchannel_command(message):
    GUILD_ID = config_discord["guild_id"]
    guild = await client.fetch_guild(GUILD_ID)
    channel = message.channel
    author = message.author
    categories = message.guild.categories

    def check(m):
        return m.channel == channel and m.author == author

    while True:
        embed = discord.Embed(
            title="In which category should the new channel be?",
            description="",
            color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        category_message = await client.wait_for('message', check=check)
        category_name = category_message.content
        for category in categories:
            if category.name == category_name:
                new_category = category
        if "new_category" in locals():
            break
        else:
            embed = discord.Embed(title="Please enter a valid category.",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await message.channel.send(embed=embed)

    embed = discord.Embed(title="What should be the channel name?",
                          description="",
                          color=discord.Colour.from_rgb(255, 0, 0))
    await message.channel.send(embed=embed)

    channel_name_message = await client.wait_for('message', check=check)
    channel_name = channel_name_message.content

    embed = discord.Embed(title=f"Created the channel {channel_name}",
                          description="",
                          color=discord.Colour.from_rgb(255, 0, 0))
    await message.channel.send(embed=embed)
    await guild.create_text_channel(channel_name, category=new_category)


def is_url_image(image_url):
    image_formats = ("image/jpg", "image/jpeg", "image/png", "image/gif")
    r = requests.head(image_url)
    if r.headers["content-type"] in image_formats:
        return True
    return False


async def additem_command(message):
    channel = message.channel
    author = message.author

    def check(m):
        return m.channel == channel and m.author == author

    while True:
        embed = discord.Embed(title="What should be the item name?",
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        item_name_message = await client.wait_for('message', check=check)
        item_name = item_name_message.content

        cart_cursor.execute(f"SELECT * FROM items WHERE name = '{item_name}'")
        if cart_cursor.fetchall() != []:
            embed = discord.Embed(
                title="You can't have 2 items with the same name.",
                description=
                "Just delete the old one or choose another name to proceed.",
                color=discord.Colour.from_rgb(255, 0, 0))
            await message.channel.send(embed=embed)
        else:
            if len(item_name) > 256:
                embed = discord.Embed(
                    title="The maximum length is 256 characters.",
                    description="",
                    color=discord.Colour.from_rgb(255, 0, 0))
                await message.channel.send(embed=embed)
            else:
                break

    while True:
        embed = discord.Embed(title="What should be the item description?",
                              description="Enter . for no description.",
                              color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        item_description_message = await client.wait_for('message',
                                                         check=check)
        item_description = item_description_message.content
        if len(item_description) > 1024:
            await message.channel.send(
                title="The maximum length is 1024 characters.",
                description="",
                color=discord.Colour.from_rgb(255, 0, 0))
        else:
            break

    while True:
        embed = discord.Embed(
            title="What should be the item image?",
            description=
            "Please enter public URL to the image \nValid Files are png, jpg, jpeg or gif. \n Enter a . for no image.",
            color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        item_image_message = await client.wait_for('message', check=check)
        item_image = item_image_message.content
        if str(item_image) == ".":
            break
        elif validators.url(item_image) == True:
            if len(item_image) > 2048:
                embed = discord.Embed(
                    title="The maximum length is 2048 characters.",
                    description="",
                    color=discord.Colour.from_rgb(255, 0, 0))
                await message.channel.send(embed=embed)
            else:
                if is_url_image(item_image) == True:
                    break
                else:
                    embed = discord.Embed(
                        title="The image url isn't the right file format.",
                        description="",
                        color=discord.Colour.from_rgb(255, 0, 0))
                    await message.channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="The image url is not public or not existing.",
                description="",
                color=discord.Colour.from_rgb(255, 0, 0))
            await message.channel.send(embed=embed)

    while True:
        embed = discord.Embed(
            title="What should be the item price?",
            description="Please enter the price like this: 0.1",
            color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        item_price_message = await client.wait_for('message', check=check)
        item_price = item_price_message.content
        try:
            item_price = round(float(item_price), 2)
            if item_price > 0:
                break
            elif item_price == 0:
                embed = discord.Embed(title="The item price can't be zero.",
                                      description="",
                                      color=discord.Colour.from_rgb(255, 0, 0))
                await message.channel.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="The item price can't be below zero",
                    description="",
                    color=discord.Colour.from_rgb(255, 0, 0))
                await message.channel.send(embed=embed)
        except ValueError:
            embed = discord.Embed(title="Please enter a valid price.",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await message.channel.send(embed=embed)

    while True:
        embed = discord.Embed(
            title="What should be the item quantity?",
            description="0 means out of stock \n-1 means unlimited",
            color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        item_quantity_message = await client.wait_for('message', check=check)
        item_quantity_database = item_quantity_message.content
        try:
            item_quantity_database = int(item_quantity_database)
            if item_quantity_database > -1:
                item_quantity = item_quantity_database
                break
            elif item_quantity_database == -1:
                item_quantity = "Unlimited"
                break
            else:
                embed = discord.Embed(
                    title="The item quantity can't be below -1(Unlimited).",
                    description="",
                    color=discord.Colour.from_rgb(255, 0, 0))
                await message.channel.send(embed=embed)
        except ValueError:
            embed = discord.Embed(title="Please enter a valid quantity.",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await message.channel.send(embed=embed)

    while True:
        embed = discord.Embed(
            title="What is the category for your item?",
            description=
            "Please mention the category channel with a # before the channel name.",
            color=discord.Colour.from_rgb(255, 0, 0))
        await message.channel.send(embed=embed)
        item_category_message = await client.wait_for('message', check=check)
        mentioned_item_category = item_category_message.raw_channel_mentions
        try:
            mentioned_item_category_id = mentioned_item_category[0]
            item_category_channel = await client.fetch_channel(
                mentioned_item_category_id)
            break
        except IndexError:
            embed = discord.Embed(title="Please mention a valid category.",
                                  description="",
                                  color=discord.Colour.from_rgb(255, 0, 0))
            await message.channel.send(embed=embed)

    embed = discord.Embed(title=item_name,
                          description="",
                          color=discord.Colour.from_rgb(255, 0, 0))

    embed.add_field(name=f"Price: {item_price}€",
                    value=item_description,
                    inline=True)
    embed.add_field(name=f"Quantity: {item_quantity}", value=".", inline=True)
    if str(item_image) != ".":
        embed.set_image(url=item_image)

    sent_item_message = await item_category_channel.send(embed=embed)
    await sent_item_message.add_reaction('🛒')
    await sent_item_message.add_reaction('❌')

    cart_cursor.execute(
        f"INSERT INTO `items` (`name`, `description`, `url`, `price`, `quantity`, `channel_id`) VALUES ('{item_name}', '{item_description}','{item_image}', '{item_price}', '{item_quantity_database}', '{mentioned_item_category_id}')"
    )
    cart_database.commit()


async def add_command(message):
    member = message.author
    cart_cursor.execute(
        f"select * from products WHERE channel = '{message.channel}' and enabled = 'true'"
    )
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

        embed = discord.Embed(title=title,
                              description="",
                              color=discord.Colour.from_rgb(255, 0, 0))

        embed.add_field(name=f"Price: {price}", value=description, inline=True)
        embed.add_field(name=f"Quantity: {quantity}", value=".", inline=True)
        if str(url) != "None":
            embed.set_image(url=url)

        await message.channel.send(embed=embed)


@client.event
async def on_message(message):
    message = message
    if message.author != client.user:
        role_names = [role.name for role in message.author.roles]
        if "Support" in role_names:
            if message.content.startswith("=help"):
                await help_command(message)
            elif message.content.startswith("=clear"):
                await delete_messages(message.channel)
            elif message.content.startswith("=addcategory"):
                await addcategory_command(message)
            elif message.content.startswith("=addchannel"):
                await addchannel_command(message)
            elif message.content.startswith("=additem"):
                await additem_command(message)
            elif message.content.startswith("=add"):
                await add_command(message)


client.run(config_discord["bot_token"])