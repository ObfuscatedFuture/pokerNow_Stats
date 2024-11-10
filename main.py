import pandas as pd
import re as re
import numpy as np


def main(arg):
    print(f"Ver: : {arg}")
    print(f"Created By : CodeSlug")
    full_log = "testData.csv"
    ledger = "ledger.csv"

    data = pd.read_csv("testData.csv")

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
    actionPattern = r"\b(calls|folds|raises|bets|checks|shows|collected|returned|posts|starting hand|ending hand|stand up|joined the game with a)\b"
    data['action'] = data['entry'].str.extract(actionPattern)
    data['action'] = data['action'].str.replace('returned', 'return')
    data['action'] = data['action'].str.replace('collected', 'collects')
    data['action'] = data['action'].str.replace('starting hand', 'new hand')
    data['action'] = data['action'].str.replace('ending hand', 'end hand')
    data['action'] = data['action'].str.replace('stand up', 'leaves')
    data['action'] = data['action'].str.replace('joined the game with a', 'joins')
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

    # Potential actions list:
    # checks, calls, raises, bets, folds
    # shows, collects, return, posts
    # new hand, end hand, leaves, joined


    player = "jlacked @ tPtOktvqpi"
    # take first hand player played
    filtered_df = data[(data['action'] == "joins") & (data['player_name'] == player)]
    print(filtered_df[['player_name', 'amount', 'action', 'hand_count']])
    p_start = int(filtered_df['hand_count'].iloc[0])

    filtered_df = data[(data['action'] == "leaves") & (data['player_name'] == player)]
    if filtered_df.empty:
        # take most recent finished hand
        print("Player is still in the game")
        p_end = int(data['hand_count'].iloc[0])

    else:
        filtered_df = data[(data['action'] == "leaves") & (data['player_name'] == player)]
        print(filtered_df[['player_name', 'amount', 'action', 'hand_count']])
        p_end = int(filtered_df['hand_count'].iloc[0])

    print("First hand: ", p_start)
    print("Last hand: ", p_end)


    data.to_csv('modified_data.csv', index=False)

if __name__ == '__main__':
    main('Ver 0.01a')


