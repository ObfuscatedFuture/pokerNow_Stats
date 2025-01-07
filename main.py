import math
import pandas as pd
import re as re
import numpy as np
from dateutil import parser
import matplotlib.pyplot as plt


def main(arg):
    print(f"{arg}")
    print(f"Created By : CodeSlug")
    full_log = "/Users/chase/Downloads/poker_now_log_pgl2UI_Dpx5U_DuQSaRPKRq8u.csv"
    ledger = "testFiles/ledger_pglrqTDi9-nBInG5U2wGN-Tbh.csv"

    data = pd.read_csv(full_log)
    ledger = pd.read_csv(ledger)

    def process_data(data):
        # Extracts Player Name to new column
        player_name_regex = r'"(.*?)"'
        data['player_name'] = data['entry'].str.extract(player_name_regex).fillna("").astype('string')
        player_nickname = r'(\S+) @'
        data['player_nickname'] = data['player_name'].str.extract(player_nickname).fillna("").astype('string')
        player_id = r'@ (\S+)$'
        data['player_id'] = data['player_name'].str.extract(player_id).fillna("").astype('string')

        # Normalize player_id based on player_nickname
        remove_dupe_names = data.groupby('player_nickname')['player_id'].first().to_dict()
        data['player_id'] = data['player_nickname'].map(remove_dupe_names)

        # Normalize player_nickname based on the updated player_id
        no_name_changes = data.groupby('player_id')['player_nickname'].first().to_dict()
        data['player_nickname'] = data['player_id'].map(no_name_changes)

        # Extracts amount of bet / stack to new column
        amount_regex = r'(\b\d+(\.\d+)?\b)'
        data['amount'] = data['entry'].str.extract(amount_regex)[0].fillna('')

        # Formats the action column
        action_pattern = r"\b(calls|folds|raises|bets|checks|shows|collected|returned|posts|starting hand|ending hand|stand up|quits the game|change|participation| stacks: #1)\b"
        data['action'] = data['entry'].str.extract(action_pattern)
        data['action'] = data['action'].str.replace('returned', 'return')
        data['action'] = data['action'].str.replace('collected', 'collects')
        data['action'] = data['action'].str.replace('starting hand', 'new hand')
        data['action'] = data['action'].str.replace('ending hand', 'end hand')
        data['action'] = data['action'].str.replace('stand up', 'leaves')
        data['action'] = data['action'].str.replace('participation', 'joins')
        data['action'] = data['action'].str.replace('quits the game', 'leaves')
        data['action'] = data['action'].str.replace(' stacks: #1', 'stacks')
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

     # TODO add time played column to modified_ledger.csv
     # add vpip separately (Probably in a method)


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
                player_nick = r'(\S+) @'
                m = re.search(player_nick, parts[1])
                name = m.group(1)
                player_id = r'@ (\S+)$'
                m = re.search(player_id, parts[1])
                id = m.group(1)
                stack = float(parts[2].strip()[1:-1])  # Extract and convert stack value
                processed.append((position, name, id, stack))
            return processed
        return None

    # implement vpip
    # creates stack data stored in stack_info

    stack_history = data["entry"].apply(process_stacks)
    stack_rows = stack_history.explode().dropna()

    stack_info = pd.DataFrame(
        stack_rows.tolist(), columns=['Position', 'player_nickname', 'player_id', 'Stack']
    )
    stack_info = pd.concat([
        data[['hand_count']].loc[stack_rows.index].reset_index(drop=True),
        stack_info
    ], axis=1)
    stack_info['hand_count'] = stack_info['hand_count'].astype(int)

    # Normalize names when player changes name mid-way through game
    no_name_changes = stack_info.groupby('player_id')['player_nickname'].first().to_dict()
    stack_info['player_nickname'] = stack_info['player_id'].map(no_name_changes)

    # Normalize IDs when player joins under 2 IDs (Or logs in mid game)*
    remove_dupes = stack_info.groupby('player_nickname')['player_id'].first().to_dict()
    stack_info['player_id'] = stack_info['player_nickname'].map(remove_dupes)

    # On leave stacks must be updated again in order to account for last played hand in data
    fix_stack = data[data['action'].isin(['leaves'])]

    fix_stack = fix_stack[['hand_count', 'amount', 'player_nickname', 'player_id']]
    fix_stack['hand_count'] = fix_stack['hand_count'].astype(int)

    fix_stack = fix_stack.rename(columns={
        'amount': 'Stack'
    }).assign(Position=-1)

    full_stack = pd.concat([stack_info, fix_stack[['hand_count', 'Position', 'player_nickname', 'player_id', 'Stack']].
                           reindex(stack_info.columns, axis=1, fill_value=None)
                            ])
    full_stack['hand_count'] = full_stack['hand_count'].astype(int)

    stack_info = full_stack
    # Sorting for profit col logic
    data = data.sort_values(by='at', ascending=True)
    stack_info = stack_info.sort_values(by='hand_count', ascending=True)

    # Currently if a player leaves and rejoins for more (or less) the stat tracker breaks
    df_join = data[data['action'].isin(['joins', 'change'])]
    df_join = df_join[['player_id', 'amount', 'hand_count', 'action']]

    for index, row in df_join.iterrows():
        id = row['player_id']
        amount = row['amount']
        action = row['action']
        hand = row['hand_count']
        is_join = False
        is_newJoin = False
        if action == 'joins':
            is_join = True
            is_newJoin = True


        s = (stack_info['hand_count'] > hand) & (stack_info['player_id'] == id)
        # If player rejoins (not first join) this if condition activates
        # This logic seems to work but is a little sloppy?
        if stack_info[(stack_info['player_id'] == id) & (stack_info['hand_count'] < hand)].shape[0] > 0:
            is_newJoin = False
            

        if is_newJoin:
            stack_info.loc[s, 'Profit'] = stack_info.loc[s, 'Stack'] - amount
            print(f"Player {id} joins at hand {hand}")
        elif is_join:
            stack_info.loc[s, 'Profit'] = (stack_info.loc[s, 'Profit'] - amount)
            print(f"Player {id} rejoins at hand {hand}")
        else: # change
            stack_info.loc[s, 'Profit'] = (stack_info.loc[s, 'Profit'] - amount)

    stack_info['Profit'] = stack_info['Profit'].fillna(0.0).round(2)
################# ^ Implemented above to Shiny ^ ####################

    # BUG SCENARIOS:
    #
    # "WARNING: the admin queued the stack change for the player ""Solstice @ VE6CjkevP7"" removing 525 chips in the next hand.",2025-01-06 23:43:47.239000+00:00,173620702723900,Solstice @ VE6CjkevP7,Solstice,VE6CjkevP7,525.0,change,Turn,274
    # "WARNING: the admin queued the stack change for the player ""DPolkPN @ IaIW3olpE5"" adding 72 chips in the next hand.",2025-01-06 23:43:50.400000+00:00,173620703040000,DPolkPN @ IaIW3olpE5,DPolkPN,IaIW3olpE5,72.0,change,Turn,274
    # "WARNING: the admin queued the stack change for the player ""DPolkPN @ IaIW3olpE5"" adding 75 chips in the next hand.",2025-01-06 23:43:54.874000+00:00,173620703487400,DPolkPN @ IaIW3olpE5,DPolkPN,IaIW3olpE5,75.0,change,Turn,274
    # ^ Does not account for sign changes (removing vs adding)

    # "The admin updated the player ""Solstice @ VE6CjkevP7"" stack from 2612 to 2087.",2025-01-06 23:44:05.776000+00:00,173620704577600,Solstice @ VE6CjkevP7,Solstice,VE6CjkevP7,2612.0,,Turn,274
    # "The admin updated the player ""DPolkPN @ IaIW3olpE5"" stack from 2447 to 2522.",2025-01-06 23:44:05.776000+00:00,173620704577601,DPolkPN @ IaIW3olpE5,DPolkPN,IaIW3olpE5,2447.0,,Turn,274
    # ^ Does not handle this situation at all


    # Calculates Hands_Played using modified_data instead of ledger file (then appends to ledger)
    # Removing reliance on ledger is a WIP so eventually this should append to a new dataFrame
    results = []
    for unique_name in stack_info['player_nickname'].unique():
        results.append({'player_nickname': unique_name, 'Hands_Played': len(stack_info[stack_info['player_nickname']==unique_name])})

    hands_played_df = pd.DataFrame(results)

    ledger = pd.merge(ledger, hands_played_df[['player_nickname', 'Hands_Played']], on='player_nickname', how='right')

    # Isolates necessary data for vpip calculations
    vpip_df = data[data['action'].isin(['calls', 'raises'])]
    vpip_df = vpip_df[['player_nickname', 'player_id','amount','action','phase','hand_count']]
    #Only counts 1x per hand played
    vpip_df = vpip_df[['player_id', 'hand_count']].drop_duplicates()

    result = vpip_df['player_id'].value_counts().to_dict()

    vpip_df = pd.DataFrame(list(result.items()), columns=['player_id', 'voluntary_put_in_pot'])
    vpip_df['voluntary_put_in_pot'] = vpip_df['voluntary_put_in_pot'].fillna(0)

    ledger = pd.merge(ledger, vpip_df[['player_id', 'voluntary_put_in_pot']], on='player_id', how='left')
    ledger['voluntary_put_in_pot'] = ((ledger['voluntary_put_in_pot']/ledger['Hands_Played'])*100).round(2)

    remade_ledger = stack_info.groupby('player_id', as_index=False).agg({
         'Stack': 'last', #This is kinda dumb and not a replacement for buy-in/buy-out
         'Profit': 'last',
         'player_nickname': 'last'
    })
    remade_ledger = pd.merge(remade_ledger, vpip_df[['player_id', 'voluntary_put_in_pot']], on='player_id', how='left')
    remade_ledger = pd.merge(remade_ledger, hands_played_df[['player_nickname', 'Hands_Played']], on='player_nickname', how='right')
    remade_ledger['voluntary_put_in_pot'] = ((remade_ledger['voluntary_put_in_pot']/remade_ledger['Hands_Played'])*100).round(2)
    remade_ledger['voluntary_put_in_pot'] = remade_ledger['voluntary_put_in_pot'].fillna(0)
    print(remade_ledger.head(2))

    # Displays profit / hand for each player, ordered highest to lowest
    # Creates new column in ledger df to store profit/hand data
    def profit_per_hand(ledger):
        profit_hand = ledger.loc[:, ['player_id', 'net', 'player_nickname', 'Hands_Played']]
        profit_hand.loc[:, 'profit_per_hand'] = ((profit_hand['net'] / profit_hand['Hands_Played'])/100).round(3)
        profit_hand = profit_hand.sort_values(by='profit_per_hand', ascending=False)
        profit_hand = profit_hand.reset_index(drop=True)
        ledger = pd.merge(ledger, profit_hand[['player_id', 'profit_per_hand']], on='player_id', how='left')
        return ledger

    ledger = profit_per_hand(ledger)

    # Append NaN to gaps in scatter plot if possible
    # Also create a 'No Data' graph to catch cases with no data
    # Creates matplot scatter plot of stack and profit as function of hand count
    def plot_stack_and_profit(stack_info, num):
        plt.figure(figsize=(10, 6))

        s_info = stack_info.copy(deep=True)
        amt_to_display = s_info['player_nickname'].unique()[:num]
        filteredSI = s_info[s_info['player_nickname'].isin(amt_to_display)]
        # Group by player and plot
        for player, group in filteredSI.groupby('player_nickname'):
            plt.plot(group['hand_count'], group['Profit'], marker='o', label=player + ' Profit')
            plt.plot(group['hand_count'], group['Stack'], marker='o', label=player + ' Stack')

        # Add labels, title, and legend
        plt.ylabel('Profit', fontsize=14)
        plt.xlabel('Hand Count', fontsize=14)
        plt.title('Player Stack & Profit vs. Hand Count', fontsize=16)
        plt.legend(title="Player", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        plt.grid(True)
        plt.tight_layout()
        # Shade the area below y=0 red
        plt.axhspan(ymin=-plt.ylim()[1], ymax=0, color='red', alpha=0.15)

        # Show the plot
        plt.show()

    # Creates matplot scatter plot of profit as function of hand count
    def plot_profit(stack_info, num):
        plt.figure(figsize=(10, 6))

        s_info = stack_info.copy(deep=True)
        amt_to_display = s_info['player_nickname'].unique()[:num]
        filteredSI = s_info[s_info['player_nickname'].isin(amt_to_display)]
        # Group by player and plot
        for player, group in filteredSI.groupby('player_nickname'):
            plt.plot(group['hand_count'], group['Profit'], marker='o', label=player + ' Profit')

        # Add labels, title, and legend
        plt.ylabel('Profit', fontsize=14)
        plt.xlabel('Hand Count', fontsize=14)
        plt.title('Player Profit vs. Hand Count', fontsize=16)
        plt.legend(title="Player", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        plt.grid(True)
        plt.tight_layout()
        # Shade the area below y=0 red
        plt.axhspan(ymin=-plt.ylim()[1], ymax=0, color='red', alpha=0.15)

        # Show the plot
        plt.show()

    def plot_stack_and_profit_for_player(stack_info, player_name):
        plt.figure(figsize=(10, 6))

        s_info = stack_info.copy(deep=True)
        filteredSI = s_info[s_info['player_nickname'] == player_name]
        # Filter for the specified player

        # Check if there is data for the specified player
        if filteredSI.empty:
            print(f"No data found for player: {player_name}")
            return

        # Plot the player's data
        plt.plot(filteredSI['hand_count'], filteredSI['Profit'], marker='o', label=player_name + ' Profit')
        plt.plot(filteredSI['hand_count'], filteredSI['Stack'], marker='o', label=player_name + ' Stack')

        # Add labels, title, and legend
        plt.ylabel('Profit', fontsize=14)
        plt.xlabel('Hand Count', fontsize=14)
        plt.title(f'{player_name} Stack & Profit vs. Hand Count', fontsize=16)
        plt.legend(title="Metric", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        plt.grid(True)
        plt.tight_layout()

        # Shade the area below y=0 red
        plt.axhspan(ymin=-plt.ylim()[1], ymax=0, color='red', alpha=0.15)

        # Show the plot
        plt.show()

    #plot_stack_and_profit(stack_info, 20)
    #plot_profit(stack_info, 20)

    #plot_stack_and_profit_for_player(stack_info, 'mcc')

    data = data.sort_values(by="at")
    stack_info.to_csv('stack_info.csv', index=False)
    ledger.to_csv('modified_ledger.csv', index=False)
    data.to_csv('modified_data.csv', index=False)



if __name__ == '__main__':
    main('Ver 0.30')


