# PokerNow Data Visualizer
### Current Version: 0.37

[See Changelog](#Changelog)

# How to use
- Clone the repository ( I am working on hosting! )
- Import necessary packages and set up [Shiny](https://shiny.posit.co/py/)
- Run the program *app.py* within the project
- You should now see this:
<img width="1437" alt="image" src="https://github.com/user-attachments/assets/eaebf710-aea8-41da-9144-f5456e77be50" />

- Now navigate to your PokerNow table and download the full log file (click ledger in the bottom left > download full log)
<img width="220" alt="image" src="https://github.com/user-attachments/assets/990b3051-b566-419a-adec-e3b9a8af02bd" />

- Upload this file to the shiny app
- *Voila* you should now see a series of stats about your game along with a graph of player performance with more features to come
<img width="1439" alt="image" src="https://github.com/user-attachments/assets/32008e4a-1c72-47fe-abc4-d67560aebafc" />

#### Planned Features
- Check the [GitHub project](https://github.com/users/ObfuscatedFuture/projects/2) for more info
- Primarily focusing on more useful poker stats such as 3 bet and 4 bet frequencies and the ability to upload multiple logs for a larger dataset

#### Changelog

Ver 0.37
 + Fixed a bug where a player leaving on the last hand would not be counted
      - Final hand winner is still not counted (KNOWN BUG)
 + Added Shinyswatch darkly theme

Ver 0.36
 + Made player name entry conditional
 + Added more comments
 + Fixed a bug where regex wouldn't match numbers in higher stakes games
 + Fixed a bug that occasionally double counted profits in certain situations

Ver 0.35
 + Migrated more code to Shiny Dashboard
 + Dashboard now supports VPIP and Profit/Hand
 + Integrated basic remade_ledger into Dashboard "Stack Info"
 
Ver 0.32
 + Moved from Shiny Express to Shiny Core for easier expandability
 + Added reactive player slider
 
Ver 0.30
 + Further reduced reliance on ledger file
 + Began Shiny Implementation
      + Added basic layout with sidebar and card layout (WIP)
      + Added base functionality with plots and CSV upload
      + Added num player slider as proof of concept & reactivity test
     
Ver 0.25
 + Implemented VPIP
 + Fixed bug that would occur when players rejoined with different names

Ver 0.24
 + Added Changelog
 + Recoded data, ledger, and stack_info to use player_nickname and player_id columns
 + Fixed bug that occurred when players logged in mid game
 + Continued VPIP implementation
 + Reduced reliance on ledger file
