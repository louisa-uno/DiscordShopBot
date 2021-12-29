import json
import mysql.connector
import discord

client = discord.Client()

with open("config.json") as f:
    config = json.load(f)
    config_mysql = config["mysql"]
    config_discord = config["discord"]


@client.event
async def on_ready():
    print("discord: Connection is working")


while True:
    print("\n[1] Quick installation")
    print(
        "[2] Test the configuration (Save the configuration before using this option.)"
    )
    print("[3] save/exit")

    option = input("Please enter the desired option:")

    if option == "1":
        config_mysql["host"] = input("Please enter your mysql host:")
        config_mysql["port"] = input("Pleasen enter your mysql port:")
        config_mysql["user"] = input("Please enter your mysql username:")
        config_mysql["password"] = input("Please enter your mysql password:")
        config_mysql["database"] = input(
            "Please enter your mysql database name:")

        config_discord["bot_token"] = input(
            "Please enter your discord bot token:")
        config_discord["guild_id"] = input(
            "Please enter the guild_id of your discord server:")
    elif option == "2":
        try:
            test_mysql = mysql.connector.connect(
                user=config_mysql["user"],
                password=config_mysql["password"],
                host=config_mysql["host"],
                port=config_mysql["port"],
                database=config_mysql["database"])
            test_mysql.close()
            print("mysql: Connection is working")
        except mysql.connector.Error as err:
            print("mysql: Something went wrong: {}".format(err))
        client.run(config_discord["bot_token"])
    elif option == "3":
        print(("Do you want to save before exiting? [y/n]"))
        option = input()
        if option == "y" or "yes":
            break
        elif option == "n" or "no":
            exit()
        else:
            print("You entered a invalid option.")

    else:
        print("Please enter a valid option number!")

with open("config.json", "w") as f:
    json.dump(config, f, indent=4, sort_keys=False)
