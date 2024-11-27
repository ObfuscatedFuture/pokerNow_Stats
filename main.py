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
    data['player_name'] = data['player_name'].fillna("").astype('string')


    # Extracts amount of bet / stack to new column
    regex = r'(\d+\.\d{2})'
    # Extract matched parts and assign them to new columns
    data['amount'] = data['entry'].str.extract(regex)
    # Fill unmatched rows with empty strings
    data['amount'] = data['amount'].fillna(-1)

    # Formats the action column
    action_pattern = r"\b(calls|folds|raises|bets|checks|shows|collected|returned|posts|starting hand|ending hand|stand up|joined the game with a|quits the game)\b"
    data['action'] = data['entry'].str.extract(action_pattern)
    data['action'] = data['action'].str.replace('returned', 'return')
    data['action'] = data['action'].str.replace('collected', 'collects')
    data['action'] = data['action'].str.replace('starting hand', 'new hand')
    data['action'] = data['action'].str.replace('ending hand', 'end hand')
    data['action'] = data['action'].str.replace('stand up', 'leaves')
    data['action'] = data['action'].str.replace('joined the game with a', 'joins')
    data['action'] = data['action'].str.replace('quits the game', 'leaves')
    data['action'] = data['action'].fillna("").astype("string")

    # Extracts the phase to new column
    phase_pattern = r"\b(starting hand|Flop|Turn|River)\b"
    data['phase'] = data['entry'].str.extract(phase_pattern)
    data['phase'] = data['phase'].str.replace('starting hand', 'Preflop')
    data['phase'] = data['phase'].bfill().astype("string")

    # Extracts the hand count to new column
    hand_count_pattern = r"^-- starting hand #(\d+)"
    data['hand_count'] = data['entry'].str.extract(hand_count_pattern)
    data['hand_count'] = data['hand_count'].bfill()
    data['hand_count'] = data['hand_count'].fillna(0).astype(int)

    data['at'] = pd.to_datetime(data['at'])
    data['amount'] = data['amount'].astype(float)

    print(data.dtypes)
    # Potential actions list:
    # checks, calls, raises, bets, folds
    # shows, collects, return, posts
    # new hand, end hand, leaves, joined
    combined_players = ledger.groupby('player_id', as_index=False).agg({
        'session_start_at': 'first',
        'session_end_at': 'last',
        'net': 'sum',  # Sum the 'score' values
        'buy_in': 'sum',
        'buy_out': 'sum',
        'stack': 'last',
        'player_nickname': 'first'
    })
    combined_players["session_start_at"] = pd.to_datetime(combined_players["session_start_at"])
    combined_players["session_end_at"] = pd.to_datetime(combined_players["session_end_at"])
    combined_players["net"] = combined_players["net"].astype(float)
    combined_players["buy_in"] = combined_players["buy_in"].astype(float)
    combined_players["buy_out"] = combined_players["buy_out"].astype(float)
    combined_players["stack"] = combined_players["stack"].astype(float)
    combined_players["player_nickname"] = combined_players["player_nickname"].astype("string")

    combined_players = combined_players.sort_values(by="player_nickname", ascending=True)

    print(combined_players.dtypes)
    player_names = combined_players['player_nickname'].tolist()
    starts = []
    ends = []
    played = []
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
                # timeStart = parser.isoparse(row['order'])
            elif row['action'] == 'leaves' and recent is not None:
                difference = row['hand_count'] - recent
                # totalTime = parser.isoparse(row['order']) - timeStart
                handsPlayed += difference
                recent = None

        starts.append(start)
        ends.append(end)
        played.append(handsPlayed)

        print(player_names[i] + " joined at hand " + str(starts[i]) + " and left at hand " + str(ends[i]) + " and played " + str(played[i]) + " hands")

        # TODO add hands Played column to modified_ledger.csv
        # TODO add time played column to modified_ledger.csv
        # TODO add vpip? column to modified_ledger.csv

        # idk ill come up with more stuff to add later
    series = pd.Series(played)
    combined_players["Hands_Played"] = series
    #Currently broken
    combined_players.to_csv('modified_ledger.csv', index=False)
    data.to_csv('modified_data.csv', index=False)

if __name__ == '__main__':
    main('Ver 0.01a')


