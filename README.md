![discord-shop](https://i.imgur.com/FIlWlKH.png)

# A user-friendly shop system for Discord

[![DeepSource](https://deepsource.io/gh/Luois45/DiscordShopBot.svg/?label=active+issues&show_trend=true&token=flPtP4Dt8HdmY9TB5GpBxgQj)](https://deepsource.io/gh/Luois45/DiscordShopBot/?ref=repository-badge)
[![Github All Releases](https://img.shields.io/github/downloads/Luois45/DiscordShopBot/total.svg)]()
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0)
[![built with: Python3](https://camo.githubusercontent.com/0d9fbff04202da688cc79c5ffe984bd171edf453b2e41e5e56e55202dd5bdbb2/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6275696c74253230776974682d507974686f6e332d7265642e737667)](https://www.python.org/)

## Add the bot to your server

- #### 1. Click on the link and add the bot with admin permissions to your Discord server
https://discord.com/api/oauth2/authorize?client_id=925539366540025917&permissions=8&scope=bot

- #### 2. The instructions about the Usage are in the [Usage section](#usage)

## Install the bot yourself

- #### 1. Install the requirements
```python
pip install -r requirements.txt
```
- #### 2. Fill out the config.json
- ##### 2.1 Fill the essentials out and test the connection using the included tool
```python
python configure.py
```
- #### 3. Start the discord-shop
```python
python discord-shop.py
```
- #### 4. Optional: Use Docker
- ##### 4.1 Create the docker image
##### Navigate first into the discord-shop folder and then enter:
```bash
docker build -t discord-shop .
```
- ##### 4.2 Upload the docker image to your server or run it on your local machine

<a name="usage"></a>
## Usage
#### You must have the "Seller" role on your server in order to use all features except the setup of the bot

- #### =setup: Runs the automatic Setup
- #### =help: Command Help
- #### =clear: Delete all messages in a channel
- #### =addcategory: Create a shop category
- #### =additem: Create a item
- #### React with ✏️ to a item to edit it.
- #### React with 🗑️ to a item to delete it.

## Contributing
#### Pull requests are welcome. For major changes, please open an issue upfront to discuss what you would like to change.

#### Please make sure to update tests as appropriate.
