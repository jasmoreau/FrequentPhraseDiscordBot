#Author: Jason Moreau
#Feel free to send questions and suggestions to m.jason77@gmail.com

import discord
from discord.ext import commands
import pymongo
from pymongo import MongoClient
import emoji

client = discord.Client() #connect to discord

def read_token(): #read token from txt file
    with open("frequentPhrase/token.txt", "r") as f:
        lines = f.readlines()
        return lines[0].strip()

def read_mongo(): #read mongo connection link
    with open("frequentPhrase/mongo.txt", 'r') as f:
        lines = f.readlines()
        return lines[0].strip()

def get_collection():
    cluster = MongoClient(read_mongo()) #create cluster for database
    db = cluster["discord"]
    collection = db["frequentPhrase"]
    return(collection)

def get_word(message):
    msg = message.content.lower().replace('!add', '').strip()
    if msg.startswith("!"):
        return False
    else:
        return message.content.lower().replace('!add', '').strip()

def get_clear_word(message):
    return message.content.lower().replace('!clear', '').strip()

def check_botmaster(roles):
    return "botmaster" in roles or "bot master" in roles

def server_exists(message): #see if the server exists
    collection = get_collection()
    if emoji.demojize(str(collection.find_one({"_id":str(message.guild.id)}))) == "None":
        return False
    return True

async def add_word(message): #adds a word if the command is correct and if the server exists in database
    if get_word(message) == False:
        await message.channel.send("No commands please! Try again.")
        return False
    else:
        word = get_word(message)
        collection = get_collection()
        if server_exists(message):
            try:
                collection.update_one({"_id":str(message.guild.id)}, {"$push":{"words":word}}) #add the word to words array in database
                collection.update_many({"server":str(message.guild.id)}, {"$set":{word:0}}) #add word to each user in the server
                return True
            except Exception as e:
                await message.channel.send("Could not add to database for some reason. Try it again! Error is " + str(e))
                await message.channel.send("No commands please! Try again.")
                return False
        else:
            await message.channel.send("Server not added properly.")
            return False

async def clear_all(message):
    collection = get_collection()
    if server_exists(message):
        try:
            for words in collection.find_one({"_id":str(message.guild.id)})['words']: #gather all the words that were added
                collection.update_many({"server":str(message.guild.id)}, {"$unset": {words:""}}) #remove the words from individual users
                collection.update_one({"_id":str(message.guild.id)}, {"$pull":{"words":words}}) #remove the words from the array in database
            return True
        except Exception as e:
            await message.channel.send("Could not remove from database for some reason. Try it again! Error is " + str(e))
            return False
    else:
        await message.channel.send("Server not added properly.")
        return False

async def clear_one(message):
    collection = get_collection()
    word = get_clear_word(message)
    if server_exists(message):
        try:
            collection.update_many({"server":str(message.guild.id)}, {"$unset": {word:""}})
            collection.update_one({"_id":str(message.guild.id)}, {"$pull":{"words":word}})
            return True
        except Exception as e:
            await message.channel.send("Could not remove " + word + " for some reason. Try it again! Error is " + str(e))
            return False
    else:
        await message.channel.send("Server not added properly.")
        return False

async def fix_server(message):
    collection = get_collection()
    guildID = str(message.guild.id)
    mbers = message.guild.members

    if server_exists(message) == False: #setting server array if it doesn't exist
        arr = []
        collection.insert_one({"_id":guildID, "words":arr})
    for mem in mbers:
        userID = str(mem.id)
        if (collection.find_one({"_id":guildID+ " " + userID}) == None): #checks if there is a an ID already
            collection.insert_one({"_id":guildID+ " " + userID, "name": mem.name, "server":guildID}) #if not then create a new one

        for words in collection.find_one({"_id":str(message.guild.id)})['words']: #cycles through the array of words
            if words not in collection.find_one({"_id":guildID+" "+userID}): #if one of the words isn't on the account then add it
                collection.update_one({"_id":guildID+" "+userID}, {"$set":{words:0}}) #add it and set it to 0

    return True

async def post_leaderboard(message):
    collection = get_collection()
    check = message.content.lower().replace('!lb', '').strip()
    mbers = message.guild.members

    if check not in collection.find_one({"_id":str(message.guild.id)})["words"]: #if the word doesn't exist then return
        await message.channel.send("Word is not assigned")

    members = [collection.find_one({"_id":str(message.guild.id)+" "+str(mem.id)})["name"] for mem in mbers] #creates the lists for the members and their numbers
    lboard = [collection.find_one({"_id":str(message.guild.id)+" "+str(mem.id)})[check] for mem in mbers]
    dict = {}
    for num in range(len(members)):
        dict[members[num]] = lboard[num] #adds together the members and their respective numbers

    final = sorted(dict.items(), key=lambda x:x[1], reverse=True) #sorts the dict by key value

    msg = check.capitalize() + " Leaderboards \n @@@@@@@@@@@@@@@@@@@@@@ \n"
    counter = 0
    try:
        for i in final:
            if counter < 3:
                msg = msg + str(i[0]) + ": " + str(i[1]) + "\n"
                counter += 1
    except Exception:
        pass

    await message.channel.send(msg)

async def my_word(message):
    collection = get_collection()
    word = message.content.lower().replace('!my', '').strip()

    if word not in collection.find_one({"_id":str(message.guild.id)})["words"]: #if the word doesn't exist then return
        await message.channel.send("Word is not assigned")
    lb = collection.find_one({"_id":str(message.guild.id)+" "+str(message.author.id)})[word]
    mem = message.author.name

    await message.channel.send(word.capitalize() + " Total\n" + mem + ": " + str(lb))



async def help(message):
    emb = discord.Embed(description="This bot is made to count frequent words or phrases in discord text! \n Commands that require the role 'BotMaster'\n\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n\n!add [word or phrase] adds a word that you want to keep track of. \n!clearall clears all the words you have added and does a fresh state. \n"
    + "!clear [word or phrase] removes it from the list of words.\n!fixserver fixes the data is it says server does not exist.\n!update adds unadded members and gives them the words."
    + "Commands that anyone can use\n\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n\n!lb [word or phrase] shows the top 3 people that said that phrase or word the most.\n!my [word or phrase] shows your count for the word or phrase.\n Any help or bugs please report to m.jason77@gmail.com",
     colour=0xf1c40f)

    await message.channel.send(embed=emb)

@client.event
async def on_ready():
    for g in client.guilds:
        print(
            f'{client.user} is connected to {g.name}'
            )
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" what you say"))


@client.event
async def on_member_join(member):
    collection = get_collection()
    guildID = str(member.guild.id)
    userID = str(member.id)
    if (collection.find_one({"_id":guildID+ " " + userID}) == None): #checks if there is a an ID already
        collection.insert_one({"_id":guildID+ " " + userID, "name": member.name, "server":guildID}) #if not then create a new one

    for words in collection.find_one({"_id":str(member.guild.id)})['words']: #cycles through the array of words
        if words not in collection.find_one({"_id":guildID+" "+userID}): #if one of the words isn't on the account then add it
            collection.update_one({"_id":guildID+" "+userID}, {"$set":{words:0}}) #add it and set it to 0

@client.event
async def on_message(message):
    roles = [role.name.lower() for role in message.author.guild.roles] #lowercases all the roles
    collection = get_collection()
    if server_exists(message) == False:
        arr = []
        collection.insert_one({"_id":str(message.guild.id), "words":arr})
    db = [words for words in collection.find_one({"_id":str(message.guild.id)})['words']]
    if len(db) > 0:
        words = [words.lower() for words in collection.find_one({"_id":str(message.guild.id)})['words']] #check if it is a valid word
    else:
        words = []
    if message.author == client.user:
        return


    for word in words:
        for w in message.content.lower().split():
            if word in w:
                collection.update_one({"_id":str(message.guild.id) + " " + str(message.author.id)}, {"$inc":{word.lower():1}})

    if message.content.lower().startswith("!lb"):
        await post_leaderboard(message)


    if message.content.lower().startswith("!help"):
        await help(message)


    if message.content.lower().startswith("!add") and check_botmaster(roles): #makes sure it is the command and they have botmaster
        if await add_word(message):
            word = get_word(message)
            await message.channel.send("Successfully added: " + word)
    elif message.content.lower().startswith("!add"):
        await message.channel.send("Do not have bot role.")


    if message.content.lower().startswith("!my"):
        await my_word(message)



    if message.content.lower() == "!clearall" and check_botmaster(roles):
        if await clear_all(message): #clear all words from database
            await message.channel.send("Successfully cleared all words.")
    elif message.content.lower() == "!clearall": #if they don't have bot master role then send message
        await message.channel.send("Do not have bot role.")
    elif message.content.lower().startswith("!clear") and check_botmaster(roles):
        if await clear_one(message):
            await message.channel.send("Successfully cleared " + get_clear_word(message))

    if message.content.lower() == "!fixserver" and check_botmaster(roles): #checks if server is good
        if await fix_server(message):
            await message.channel.send("Fix was successful!")
    elif message.content.lower() == "!fixserver":
        await message.channel.send("Do not have bot role.")

    if message.content.lower() == "!update" and check_botmaster(roles): #add all new users and fix server
        if await fix_server(message):
            await message.channel.send("Successfully updated!")

@client.event
async def on_guild_join(guild):
    guildID = str(guild.id)
    mbers = guild.members
    collection = get_collection()
    for mem in mbers:
        userID = str(mem.id)
        if (collection.find_one({"_id":guildID+ " " + userID}) == None):
            collection.insert_one({"_id":guildID+ " " + userID, "name": mem.name, "server":guildID})

    if (collection.find_one({"_id":guildID}) == None):
        arr = []
        collection.insert_one({"_id":guildID, "words":arr})

    for channel in guild.text_channels:
        try:
            await channel.send("Hello World! I will count how often this discord says certain words or phrases. Use !help for more info. To add words users require BotMaster role.")
            break
        except Exception:
            pass
        else:
            break


token = read_token()
client.run(token) #start bot
