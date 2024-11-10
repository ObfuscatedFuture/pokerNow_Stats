import math

import pandas as pd
import re as re
import numpy as np
from dateutil import parser


def main(arg):
    print(f"Ver: : {arg}")
    print(f"Created By : CodeSlug")
    full_log = "testData.csv"
    ledger = "ledger.csv"

    data = pd.read_csv(full_log)
    ledger = pd.read_csv(ledger)

    # Extracts Player Name to new column
    regex = r'"(.*?)"'
    # Extract matched parts and assign them to new columns
    data['player_name'] = data['entry'].str.extract(regex)
    # Fill unmatched rows with empty strings
    data['player_name'] = data['player_name'].fillna("")

    # Extracts amount of bet / stack to new column
    regex = r'(\d+\.\d{2})'
    # Extract matched parts and assign them to new columns
    data['amount'] = data['entry'].str.extract(regex)
    # Fill unmatched rows with empty strings
    data['amount'] = data['amount'].fillna("")

    joinGamePattern = r"^The player \".*?\" joined the game with a stack of .*?\.$"
    playerJoins = data.loc[data['entry'].str.contains(joinGamePattern)]

    # Formats the action column
    actionPattern = r"\b(calls|folds|raises|bets|checks|shows|collected|returned|posts|starting hand|ending hand|stand up|joined the game with a|quits the game)\b"
    data['action'] = data['entry'].str.extract(actionPattern)
    data['action'] = data['action'].str.replace('returned', 'return')
    data['action'] = data['action'].str.replace('collected', 'collects')
    data['action'] = data['action'].str.replace('starting hand', 'new hand')
    data['action'] = data['action'].str.replace('ending hand', 'end hand')
    data['action'] = data['action'].str.replace('stand up', 'leaves')
    data['action'] = data['action'].str.replace('joined the game with a', 'joins')
    data['action'] = data['action'].str.replace('quits the game', 'leaves')
    data['action'] = data['action'].fillna("")

    # Extracts the phase to new column
    phasePattern = r"\b(starting hand|Flop|Turn|River)\b"
    data['phase'] = data['entry'].str.extract(phasePattern)
    data['phase'] = data['phase'].str.replace('starting hand', 'Preflop')
    data['phase'] = data['phase'].bfill()

    # Extracts the hand count to new column
    handCountPattern = r"^-- starting hand #(\d+)"
    data['hand_count'] = data['entry'].str.extract(handCountPattern)
    data['hand_count'] = data['hand_count'].bfill()
    data['hand_count'] = data['hand_count'].fillna(0).astype(int)

    # Potential actions list:
    # checks, calls, raises, bets, folds
    # shows, collects, return, posts
    # new hand, end hand, leaves, joined
    combinedPlayers = ledger.groupby('player_id', as_index=False).agg({
        'session_start_at': 'first',
        'session_end_at': 'last',
        'net': 'sum',  # Sum the 'score' values
        'buy_in': 'sum',
        'buy_out': 'sum',
        'stack': 'last',
        'player_nickname': 'first'
    })
    player_names = combinedPlayers['player_nickname'].tolist()
    for i in range(len(player_names)):
        regex = r'' + player_names[i] + ''

        handsPlayed = 0

        playerData = data[data['player_name'].str.contains(regex)]
        end = playerData.loc[playerData['action'] == 'leaves', 'hand_count'].astype(int).max()
        start = playerData['hand_count'].astype(int).min()+1

        if math.isnan(end):
            end = playerData['hand_count'].astype(int).max()
            handsPlayed = end-start

        playerData = playerData[playerData['action'].isin(['joins', 'leaves'])]

        recent = None
        playerData.sort_values(by=['hand_count'], inplace=True, ascending=True)

        for index, row in playerData.iterrows():
            if row['action'] == 'joins' and recent is None:
                recent = row['hand_count']
                #timeStart = parser.isoparse(row['order'])
            elif row['action'] == 'leaves' and recent is not None:
                difference = row['hand_count'] - recent
                #totalTime = parser.isoparse(row['order']) - timeStart
                handsPlayed += difference
                recent = None




        # Get the components of the timedelta
        #print(totalTime)
        #hours, remainder = divmod(totalTime, 3600)
        #minutes, seconds = divmod(remainder, 60)

        # Format as hours:minutes:seconds
        #formatted_difference = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        #print(formatted_difference)

        print(player_names[i] + " joined at hand " + str(start) + " and left at hand " + str(end) + " and played " + str(handsPlayed) + " hands")

        #TODO add hands Played column to modified_ledger.csv
        #TODO add time played column to modified_ledger.csv
        #TODO add vpip? column to modified_ledger.csv

        #idk ill come up with more stuff to add later




    combinedPlayers.to_csv('modified_ledger.csv', index=False)
    data.to_csv('modified_data.csv', index=False)

if __name__ == '__main__':
    main('Ver 0.01a')


