import faicons as fa
import plotly.express as px
import pandas as pd
import re
import numpy as np
from dateutil import parser
import matplotlib.pyplot as plt

from shiny import App, ui, reactive, render, req
from shinywidgets import render_plotly
from shiny.express import input, render, ui
from shinywidgets import render_widget


ui.page_opts(title="PokerNow Data Visualizer", fillable=True)


with ui.sidebar():
        ui.input_file("csv_file", "Upload CSV", accept=[".csv"]),
        ui.input_slider("val", "Players", min=0, max=10, value=10)
        ui.input_text("text", "Specific Player", value="Chase")
        

with ui.navset_card_underline(title="Plots"):
    with ui.nav_panel("Player Stacks & Profit"):
        @render.plot
        def plot_stack_and_profit():
            f = req(input.csv_file())
            if(stack_info is None or stack_info.empty):
                return
            plt.figure(figsize=(10, 6))
            s_info = stack_info.copy(deep=True)
            amt_to_display = s_info['player_nickname'].unique()[:input.val()]
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

    with ui.nav_panel("Player Stacks"):
        @render.plot
        def plot_profit():
            f = req(input.csv_file())
            if(stack_info is None or stack_info.empty):
                return
            plt.figure(figsize=(10, 6))
            s_info = stack_info.copy(deep=True)
            amt_to_display = s_info['player_nickname'].unique()[:input.val()]
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
    
stack_info = None
data = None


        
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
            amount_regex = r'(\d+\.\d{2})'
            data['amount'] = data['entry'].str.extract(amount_regex).fillna('')

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

@reactive.Effect
def get_data():
        """Load and preprocess the uploaded CSV file."""
        f = req(input.csv_file())
        global data
        global stack_info
        data = pd.read_csv(f[0]["datapath"])

        data = process_data(data)
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


            s = (stack_info['hand_count'] > hand) & (stack_info['player_id'] == id)
            # If player rejoins (not first join) this if condition activates
            # This logic seems to work but is a little sloppy?
            if stack_info[(stack_info['player_id'] == id) & (stack_info['hand_count'] < hand)].shape[0] > 0:
                is_newJoin = False

            if is_join:
                stack_info.loc[s, 'Profit'] = stack_info.loc[s, 'Stack'] - amount
            elif not is_newJoin:
                stack_info.loc[s, 'Profit'] = (stack_info.loc[s, 'Stack'] - amount) + stack_info.loc[s, 'Profit']
            else:
                stack_info.loc[s, 'Profit'] = (stack_info.loc[s, 'Profit'] - amount)

        stack_info['Profit'] = stack_info['Profit'].fillna(0.0).round(2)
        print("Data loaded and processed.")


@render.text
def slider_val():
    return f"Slider value: {input.val()}"
    




