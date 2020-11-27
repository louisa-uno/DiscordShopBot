![discord-shop](https://i.imgur.com/FIlWlKH.png)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/4ac1a9bf94584ad0b8b8e01a0e22eb26)](https://app.codacy.com/gh/Luois45/discord-shop?utm_source=github.com&utm_medium=referral&utm_content=Luois45/discord-shop&utm_campaign=Badge_Grade_Settings)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0)
[![built with: Python3](https://camo.githubusercontent.com/0d9fbff04202da688cc79c5ffe984bd171edf453b2e41e5e56e55202dd5bdbb2/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f6275696c74253230776974682d507974686f6e332d7265642e737667)](https://www.python.org/)

### A user-friendly shop system for discord

## Installation

- #### 1. Install the requirements.txt
```python
pip install -r requirements.txt
```
- #### 2. Fill out the config.json
- ##### 2.1 Fill the essentials out and test the connection using the included tool
```python
python configure.py
```
- ##### 2.2 Optional: Set custom messages using the config.json
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

## Usage
#### You must have the "Support" role on your server in order to use the bot.

- #### =help: Command Help
- #### =clear: Delete all messages in a channel
- #### =addcategory: Create a shop category
- #### =additem: Create a item
- #### React with ✏️ to a item to edit it.

## Contributing
#### Pull requests are welcome. For major changes, please open an issue upfront to discuss what you would like to change.

#### Please make sure to update tests as appropriate.