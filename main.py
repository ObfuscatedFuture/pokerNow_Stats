import math
import pandas as pd
import re as re
import numpy as np
from dateutil import parser
import matplotlib.pyplot as plt


def main(arg):
    print(f"{arg}")
    print(f"Created By : CodeSlug")
    full_log = "testFiles/poker_now_log_pglrqTDi9-nBInG5U2wGN-Tbh.csv"
    ledger = "testFiles/ledger_pglrqTDi9-nBInG5U2wGN-Tbh.csv"

    data = pd.read_csv(full_log)
    ledger = pd.read_csv(ledger)

    def process_data(data):
        # Extracts Player Name to new column
        player_name_regex = r'"(.*?)"'
        data['player_name'] = data['entry'].str.extract(player_name_regex).fillna("").astype('string')

        # Extracts amount of bet / stack to new column
        amount_regex = r'(\d+\.\d{2})'
        data['amount'] = data['entry'].str.extract(amount_regex).fillna('')

        # Formats the action column
        action_pattern = r"\b(calls|folds|raises|bets|checks|shows|collected|returned|posts|starting hand|ending hand|stand up|quits the game|change|participation)\b"
        data['action'] = data['entry'].str.extract(action_pattern)
        data['action'] = data['action'].str.replace('returned', 'return')
        data['action'] = data['action'].str.replace('collected', 'collects')
        data['action'] = data['action'].str.replace('starting hand', 'new hand')
        data['action'] = data['action'].str.replace('ending hand', 'end hand')
        data['action'] = data['action'].str.replace('stand up', 'leaves')
        data['action'] = data['action'].str.replace('participation', 'joins')
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
        data['hand_count'] = data['hand_count'].bfill().fillna(0).astype(int)

        data['at'] = pd.to_datetime(data['at'])
        data['amount'] = pd.to_numeric(data['amount'], errors='coerce')

        return data

    def process_ledger(ledger):
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

        return combined_players

    data = process_data(data)
    ledger = process_ledger(ledger)

    # hand count calculations
    player_names = ledger['player_nickname'].tolist()
    starts = []
    ends = []
    played = []
    # This is somewhat efficient (only running through each unique player_name)
    for i in range(len(player_names)):
        regex = r'' + player_names[i] + ''

        hands_played = 0

        player_data = data[data['player_name'].str.contains(regex)]
        end = player_data.loc[player_data['action'] == 'leaves', 'hand_count'].astype(int).max()
        start = player_data['hand_count'].astype(int).min()+1

        if math.isnan(end):
            end = player_data['hand_count'].astype(int).max()
            hands_played = end-start

        player_data = player_data[player_data['action'].isin(['joins', 'leaves'])]

        recent = None
        player_data = player_data.sort_values(by=['at'], ascending=True)

        #This is buggy and fails in certain cases (but idk why or exactly when so more testing is required)
        for _, row in player_data.iterrows():
            if row['action'] == 'joins' and recent is None:
                recent = row['hand_count']
            elif row['action'] == 'leaves' and recent is not None:
                difference = row['hand_count'] - recent
                hands_played += difference
                recent = None

        starts.append(start)
        ends.append(end)
        played.append(hands_played)

        # TODO add time played column to modified_ledger.csv
        # TODO add vpip? column to modified_ledger.csv
######################

#######################################
    # Processing for stack_info dataFrame
    def process_stacks(row):
        if row.startswith("Player stacks:"):
            stacks = row[len("Player stacks:"):].strip()
            players = stacks.split(" | ")
            processed = []
            for player in players:
                parts = player.split('"')
                position = parts[0].strip()
                name = parts[1]
                stack = float(parts[2].strip()[1:-1])  # Extract and convert stack value
                processed.append((position, name, stack))
            return processed
        return None

    # implement vpip
    # creates stack data stored in stack_info
    stack_history = data["entry"].apply(process_stacks)
    stack_rows = stack_history.explode().dropna()

    stack_info = pd.DataFrame(
    stack_rows.tolist(), columns=['Position', 'Player', 'Stack']
    )
    stack_info = pd.concat([
        data[['hand_count']].loc[stack_rows.index].reset_index(drop=True),
        stack_info
    ], axis=1)
    # logic to create profit / stack x hands played graphs
    data = data.sort_values(by=['at'], ascending=True)
    stack_info.sort_values(by=['hand_count'], ascending=True)

    # Currently if a player leaves and rejoins for more (or less) the stat tracker breaks
    df_join = data[data['action'].isin(['joins', 'change'])]
    df_join = df_join[['player_name', 'amount', 'hand_count', 'action']]

    for index, row in df_join.iterrows():
        player = row['player_name']
        amount = row['amount']
        action = row['action']
        hand = row['hand_count']
        is_change = False
        if action=='change':
            is_change = True

        s = (stack_info['hand_count'] > hand) & (stack_info['Player'] == player)

        if not is_change:
            stack_info.loc[s, 'Profit'] = stack_info.loc[s, 'Stack'] - amount
        else:
            stack_info.loc[s, 'Profit'] = stack_info.loc[s, 'Profit'] - amount

    # Rounds profit to cents (removes floating point errors) [could replace with lamda expression]
    # This is for some reason just a hair off (~2% or less) on all stacks
    # Need to investigate more as to the cause of the issue
    stack_info['Profit'] = stack_info['Profit'].fillna(0.0).apply(lambda x: math.trunc(x * 100) / 100)

    plt.figure(figsize=(10, 6))
    top_ten_names = stack_info['Player'].unique()[:5]
    filteredSI = stack_info[stack_info['Player'].isin(top_ten_names)]
    # Group by player and plot
    for player, group in filteredSI.groupby('Player'):
        plt.plot(group['hand_count'], group['Profit'], marker='o', label=player)
        plt.plot(group['hand_count'], group['Stack'], marker='o', label=player)

    # Add labels, title, and legend
    plt.ylabel('Profit', fontsize=14)
    plt.xlabel('Hand Count', fontsize=14)
    plt.title('Player Profit vs. Hand Count', fontsize=16)
    plt.legend(title="Player", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    plt.grid(True)
    plt.tight_layout()

    # Show the plot
    plt.show()

    series = pd.Series(played)
    ledger["Hands_Played"] = series

    ledger.to_csv('modified_ledger.csv', index=False)
    data.to_csv('modified_data.csv', index=False)

    stack_info.to_csv('stack_info.csv', index=False)

if __name__ == '__main__':
    main('Ver 0.2')


