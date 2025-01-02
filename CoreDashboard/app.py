import faicons as fa
import plotly.express as px
import pandas as pd
import re
import numpy as np
from dateutil import parser
import matplotlib.pyplot as plt

from shiny import App, ui, reactive, render, req
from shinywidgets import render_plotly
from shinywidgets import render_widget

from shiny import ui

# PokerNow Data Visualizer
# Written by Chase LaBarre // Obfuscated Future

# Version 0.35
ver = "0.35"

ICONS = {
    "user": fa.icon_svg("user", "regular"),
    "wallet": fa.icon_svg("wallet"),
    "currency-dollar": fa.icon_svg("dollar-sign"),
    "gear": fa.icon_svg("gear")
}

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_file("csv_file", "Upload CSV", accept=[".csv"]),
        ui.input_text("text", "Specific Player", value="Chase"),
        ui.output_ui("conditional_slider")
    ),
    # Main panel content with tabs
    ui.card(
    ui.navset_tab(
        ui.nav_panel(
            "Player Stacks & Profit",
            ui.output_plot("plot_stacks_and_profits", width="100%", height="400px")
        ),
        ui.nav_panel(
            "Player Profit",
            ui.output_plot("plot_profits", width="100%", height="400px")
        ),
        ui.nav_panel(
            "Specific Player",
            ui.output_plot("plot_player", width="100%", height="400px")
        )
    )
    ),
    ui.card(
            ui.card_header(
                "Stack Info",
                ui.popover(
                    ICONS["gear"],
                    ui.input_radio_buttons(
                        "sort_var", "Sort By:",
                        ["player_nickname", "vpip", "profit_per_hand", "idk"],
                        selected="day",
                        inline=True,
                    ),
                    title="Add a color variable",
                ),
                class_="d-flex justify-content-between align-items-center",
            ),
            ui.output_data_frame("stack_frame"),
    ),
    title="PokerNow Data Visualizer V"+ ver,
    fillable=True,
)


def server(input, output, session):
    stackinfo = reactive.Value(None)
    databank = reactive.Value(None)
    remadeledger = reactive.Value(None)
    

    @reactive.Effect
    def get_data():
        """Load and preprocess the uploaded CSV file."""
        f = req(input.csv_file())
        data = pd.read_csv(f[0]["datapath"])

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

        stackinfo.set(stack_info)
        databank.set(data)

        results = []
        for unique_name in stack_info['player_nickname'].unique():
            results.append({'player_nickname': unique_name, 'Hands_Played': len(stack_info[stack_info['player_nickname']==unique_name])})

        hands_played_df = pd.DataFrame(results)

        # Isolates necessary data for vpip calculations
        vpip_df = data[data['action'].isin(['calls', 'raises'])]
        vpip_df = vpip_df[['player_nickname', 'player_id','amount','action','phase','hand_count']]
        #Only counts 1x per hand played
        vpip_df = vpip_df[['player_id', 'hand_count']].drop_duplicates()

        result = vpip_df['player_id'].value_counts().to_dict()

        vpip_df = pd.DataFrame(list(result.items()), columns=['player_id', 'voluntary_put_in_pot'])
        vpip_df['voluntary_put_in_pot'] = vpip_df['voluntary_put_in_pot'].fillna(0)
        
        remade_ledger = stack_info.groupby('player_id', as_index=False).agg({
            'Stack': 'last', #This is kinda dumb and not a replacement for buy-in/buy-out
            'Profit': 'last',
            'player_nickname': 'last'
        })
        remade_ledger = pd.merge(remade_ledger, vpip_df[['player_id', 'voluntary_put_in_pot']], on='player_id', how='left')
        remade_ledger = pd.merge(remade_ledger, hands_played_df[['player_nickname', 'Hands_Played']], on='player_nickname', how='right')
        remade_ledger['voluntary_put_in_pot'] = ((remade_ledger['voluntary_put_in_pot']/remade_ledger['Hands_Played'])*100).round(2)
        remade_ledger['voluntary_put_in_pot'] = remade_ledger['voluntary_put_in_pot'].fillna(0)
        remade_ledger['voluntary_put_in_pot'] = remade_ledger['voluntary_put_in_pot'].apply(lambda x: f"{x:.1f}%")

        remade_ledger = remade_ledger[['player_nickname', 'player_id', 'Stack', 'Profit', 'voluntary_put_in_pot', 'Hands_Played']]

        def profit_per_hand(ledger):
            profit_hand = ledger.loc[:, ['player_id', 'Profit', 'player_nickname', 'Hands_Played']]
            profit_hand.loc[:, 'profit_per_hand'] = ((profit_hand['Profit'] / profit_hand['Hands_Played'])).round(3)
            profit_hand = profit_hand.sort_values(by='profit_per_hand', ascending=False)
            profit_hand = profit_hand.reset_index(drop=True)
            ledger = pd.merge(ledger, profit_hand[['player_id', 'profit_per_hand']], on='player_id', how='left')
            ledger['profit_per_hand'] = ledger['profit_per_hand'].apply(lambda x: f"${x:.1f}")
            return ledger

        remade_ledger = profit_per_hand(remade_ledger)
        remadeledger.set(remade_ledger)

        print("Data loaded and processed.")

    def get_unique_players(data):
        si = stackinfo.get()
        if data is None:
            return 0
        return si['player_id'].nunique()
    
    @render.data_frame
    def stack_frame():
        f = req(input.csv_file())
        return render.DataGrid(remadeledger.get())
    
    @render.ui
    def conditional_slider():
        df = databank.get()
        if df is None:
            return
        else:
            # Return a slider input once the data is processed
            return ui.input_slider("val", "Players", min=0, max= get_unique_players(df), value=10)

    @render.plot
    def plot_player():
            stack_info = stackinfo.get()
            player_name = input.text()
            if(stack_info is None):
                fig, ax = plt.subplots()
                ax.text(0.5, 0.5, "Awaiting Data...", fontsize=16, ha="center", va="center")
                plt.axis("off")
                return fig
            plt.figure(figsize=(10, 6))

            s_info = stack_info.copy(deep=True)
            filteredSI = s_info[s_info['player_nickname'] == player_name]
            # Filter for the specified player

            # Check if there is data for the specified player
            if filteredSI.empty:
                fig, ax = plt.subplots()
                ax.text(0.5, 0.5, "No Player with name '"+player_name+"'", fontsize=16, ha="center", va="center")
                plt.axis("off")
                return fig

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

    @render.plot
    def plot_profits():
            stack_info = stackinfo.get()
            if(stack_info is None):
                fig, ax = plt.subplots()
                ax.text(0.5, 0.5, "Awaiting Data...", fontsize=16, ha="center", va="center")
                plt.axis("off")
                return fig
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

    @render.plot
    def plot_stacks_and_profits():
            stack_info = stackinfo.get()
            if(stack_info is None):
                fig, ax = plt.subplots()
                ax.text(0.5, 0.5, "Awaiting Data...", fontsize=16, ha="center", va="center")
                plt.axis("off")
                return fig
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


app = App(app_ui, server)
