#!/usr/bin/env python3
"""
FRC Scouting System - Data Analysis Dashboard
Streamlit dashboard for analyzing scouting data and creating pick lists
"""

import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import altair as alt


class ScoutingDashboard:
    def __init__(self, db_path=None):
        # Use environment variable for Docker deployment, fallback to local
        import os
        self.db_path = db_path or os.getenv('DB_PATH', 'scouting_data.db')
    
    def load_data(self):
        """Load data from SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Load raw scouting data and calculate aggregates per team
            query = """
            SELECT 
                team_number,
                AVG(auto_balls_scored_upper + auto_balls_scored_lower) as Avg_Auto,
                AVG(teleop_balls_scored_upper + teleop_balls_scored_lower) as Avg_Teleop,
                AVG(CASE 
                    WHEN climb_level = 'Traversal' THEN 1.0
                    WHEN climb_level = 'High' THEN 0.75
                    WHEN climb_level = 'Mid' THEN 0.5
                    WHEN climb_level = 'Low' THEN 0.25
                    ELSE 0.0
                END) as Climb_Success_Rate,
                AVG(CASE 
                    WHEN defense_rating = 'Excellent' THEN 4.0
                    WHEN defense_rating = 'Good' THEN 3.0
                    WHEN defense_rating = 'Average' THEN 2.0
                    WHEN defense_rating = 'Poor' THEN 1.0
                    ELSE 0.0
                END) as Defense_Rating,
                COUNT(*) as Matches_Played
            FROM scouting_data
            GROUP BY team_number
            ORDER BY team_number
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def load_raw_data(self):
        """Load raw scouting data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT * FROM scouting_data ORDER BY id DESC"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading raw data: {e}")
            return pd.DataFrame()
    
    def load_team_match_data(self, team_number):
        """Load entry-by-entry data for a specific team"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT 
                id,
                (auto_balls_scored_upper + auto_balls_scored_lower) as auto_score,
                (teleop_balls_scored_upper + teleop_balls_scored_lower) as teleop_score,
                CASE 
                    WHEN climb_level IN ('Traversal', 'High', 'Mid', 'Low') THEN 1
                    ELSE 0
                END as climbed
            FROM scouting_data
            WHERE team_number = ?
            ORDER BY id
            """
            df = pd.read_sql_query(query, conn, params=[team_number])
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading team data: {e}")
            return pd.DataFrame()
    
    def pick_list_formulation_tab(self):
        """Pick List Formulation tab implementation"""
        st.header("Pick List Formulation")
        st.markdown("Calculate weighted scores for teams and identify top picks.")
        
        # Load data
        df = self.load_data()
        
        if df.empty:
            st.warning("No scouting data available. Please scan some QR codes first!")
            st.info("To get started, run `python3 scanner.py` and scan some scouting data QR codes.")
            return
        
        # Sidebar - Weight Sliders
        st.sidebar.header("Weight Configuration")
        st.sidebar.markdown("Adjust weights to customize team rankings")
        
        auto_weight = st.sidebar.slider(
            "Auto Weight",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Weight for autonomous performance"
        )
        
        teleop_weight = st.sidebar.slider(
            "Teleop Weight",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Weight for teleoperated performance"
        )
        
        climb_weight = st.sidebar.slider(
            "Climb Weight",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Weight for climbing success rate"
        )
        
        defense_weight = st.sidebar.slider(
            "Defense Weight",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Weight for defense rating"
        )
        
        # Calculate Weighted Score
        df['Weighted_Score'] = (
            (df['Avg_Auto'] * auto_weight) +
            (df['Avg_Teleop'] * teleop_weight) +
            (df['Climb_Success_Rate'] * climb_weight) +
            (df['Defense_Rating'] * defense_weight)
        )
        
        # Sort by Weighted Score descending
        df = df.sort_values('Weighted_Score', ascending=False).reset_index(drop=True)
        
        # Initialize DNP (Do Not Pick) in session state if not exists
        if 'dnp_teams' not in st.session_state:
            st.session_state.dnp_teams = set()
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Teams", len(df))
        with col2:
            first_picks = len([i for i in range(min(8, len(df))) if df.iloc[i]['team_number'] not in st.session_state.dnp_teams])
            st.metric("First Pick Candidates", first_picks)
        with col3:
            second_picks = len([i for i in range(8, min(24, len(df))) if df.iloc[i]['team_number'] not in st.session_state.dnp_teams])
            st.metric("Second Pick Candidates", second_picks)
        
        st.markdown("---")
        
        # Create display dataframe with DNP column
        display_df = df.copy()
        display_df.insert(0, 'DNP', False)
        display_df.insert(1, 'Rank', range(1, len(display_df) + 1))
        
        # Round numerical columns for better display
        display_df['Avg_Auto'] = display_df['Avg_Auto'].round(2)
        display_df['Avg_Teleop'] = display_df['Avg_Teleop'].round(2)
        display_df['Climb_Success_Rate'] = display_df['Climb_Success_Rate'].round(2)
        display_df['Defense_Rating'] = display_df['Defense_Rating'].round(2)
        display_df['Weighted_Score'] = display_df['Weighted_Score'].round(2)
        
        # Rename columns for better display
        display_df = display_df.rename(columns={
            'team_number': 'Team',
            'Matches_Played': 'Matches'
        })
        
        st.subheader("Team Rankings")
        
        # Create interactive table with DNP checkboxes
        for idx, row in display_df.iterrows():
            team = row['Team']
            rank = row['Rank']
            
            # Determine highlight color
            if rank <= 8:
                highlight = "[1st Pick]"
                color = "#FFD700"
            elif rank <= 24:
                highlight = "[2nd Pick]"
                color = "#C0C0C0"
            else:
                highlight = ""
                color = None
            
            # Create columns for each row
            cols = st.columns([0.5, 0.5, 1, 1, 1, 1, 1, 1, 1])
            
            with cols[0]:
                # DNP checkbox
                dnp_key = f"dnp_{team}_{idx}"
                is_dnp = st.checkbox(
                    "",
                    value=team in st.session_state.dnp_teams,
                    key=dnp_key,
                    help=f"Mark Team {team} as Do Not Pick"
                )
                if is_dnp:
                    st.session_state.dnp_teams.add(team)
                else:
                    st.session_state.dnp_teams.discard(team)
            
            with cols[1]:
                st.markdown(f"{highlight} **{rank}**")
            
            with cols[2]:
                if color and team not in st.session_state.dnp_teams:
                    st.markdown(f"<span style='background-color: {color}; padding: 5px; border-radius: 3px;'>**Team {team}**</span>", unsafe_allow_html=True)
                elif team in st.session_state.dnp_teams:
                    st.markdown(f"<span style='text-decoration: line-through; color: gray;'>Team {team}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**Team {team}**")
            
            with cols[3]:
                st.text(f"{row['Avg_Auto']:.2f}")
            
            with cols[4]:
                st.text(f"{row['Avg_Teleop']:.2f}")
            
            with cols[5]:
                st.text(f"{row['Climb_Success_Rate']:.2f}")
            
            with cols[6]:
                st.text(f"{row['Defense_Rating']:.2f}")
            
            with cols[7]:
                st.text(f"{row['Weighted_Score']:.2f}")
            
            with cols[8]:
                st.text(f"{row['Matches']}")
        
        # Legend
        st.markdown("---")
        st.markdown("### Legend")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<span style='background-color: #FFD700; padding: 5px; border-radius: 3px;'>**Gold (Top 8)**</span> - First Pick Candidates", unsafe_allow_html=True)
        with col2:
            st.markdown("<span style='background-color: #C0C0C0; padding: 5px; border-radius: 3px;'>**Silver (9-24)**</span> - Second Pick Candidates", unsafe_allow_html=True)
        
        # Export filtered pick list
        st.markdown("---")
        if st.button("Export Pick List (Excluding DNP)"):
            export_df = display_df[~display_df['Team'].isin(st.session_state.dnp_teams)]
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download Pick List CSV",
                data=csv,
                file_name="pick_list.csv",
                mime="text/csv"
            )
            st.success("Pick list ready for download!")
    
    def team_analysis_tab(self):
        """Team Analysis tab implementation"""
        st.header("Team Analysis")
        st.markdown("Analyze individual team performance with detailed metrics and charts.")
        
        # Load data
        df = self.load_data()
        
        if df.empty:
            st.warning("No scouting data available. Please scan some QR codes first!")
            st.info("To get started, run `python3 scanner.py` and scan some scouting data QR codes.")
            return
        
        # Sidebar - Team Selection
        st.sidebar.header("Team Selection")
        team_options = sorted(df['team_number'].tolist())
        
        if not team_options:
            st.warning("No teams available in the database.")
            return
        
        selected_team = st.sidebar.selectbox(
            "Select Team Number",
            options=team_options,
            help="Choose a team to analyze their performance"
        )
        
        # Get team stats
        team_stats = df[df['team_number'] == selected_team].iloc[0]
        
        # Display team header
        st.subheader(f"Team {selected_team}")
        st.markdown(f"**Matches Played:** {team_stats['Matches_Played']}")
        
        st.markdown("---")
        
        # Metric Cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Avg Auto Score",
                value=f"{team_stats['Avg_Auto']:.2f}",
                help="Average autonomous period score"
            )
        
        with col2:
            st.metric(
                label="Avg Teleop Score",
                value=f"{team_stats['Avg_Teleop']:.2f}",
                help="Average teleoperated period score"
            )
        
        with col3:
            climb_pct = team_stats['Climb_Success_Rate'] * 100
            st.metric(
                label="Climb %",
                value=f"{climb_pct:.0f}%",
                help="Climb success rate percentage"
            )
        
        st.markdown("---")
        
        # Load match-by-match data for this team
        match_data = self.load_team_match_data(selected_team)
        
        if not match_data.empty:
            # Line Chart - Score Evolution
            st.subheader("Score Evolution Over Entries")
            
            # Prepare data for chart
            chart_data = match_data[['id', 'auto_score', 'teleop_score']].copy()
            chart_data['total_score'] = chart_data['auto_score'] + chart_data['teleop_score']
            
            # Create line chart using Altair
            base = alt.Chart(chart_data).encode(
                x=alt.X('id:Q', title='Entry ID')
            )
            
            auto_line = base.mark_line(color='blue', point=True).encode(
                y=alt.Y('auto_score:Q', title='Score'),
                tooltip=['id', 'auto_score']
            )
            
            teleop_line = base.mark_line(color='green', point=True).encode(
                y=alt.Y('teleop_score:Q', title='Score'),
                tooltip=['id', 'teleop_score']
            )
            
            total_line = base.mark_line(color='red', point=True).encode(
                y=alt.Y('total_score:Q', title='Score'),
                tooltip=['id', 'total_score']
            )
            
            chart = (auto_line + teleop_line + total_line).properties(
                width=700,
                height=400
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            )
            
            st.altair_chart(chart, use_container_width=True)
            
            # Legend
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Auto Score** (Blue)")
            with col2:
                st.markdown("**Teleop Score** (Green)")
            with col3:
                st.markdown("**Total Score** (Red)")
        
        st.markdown("---")
        
        # Heatmap Placeholder - Starting Positions
        st.subheader("Starting Position Analysis")
        st.info("Starting position data is not currently collected. This feature will be available when position tracking is implemented in the scouting form.")
        
        # Show a placeholder scatter plot
        st.markdown("**Example Visualization:**")
        placeholder_data = pd.DataFrame({
            'x': [0, 1, 2, 0, 1, 2],
            'y': [0, 0, 0, 1, 1, 1],
            'frequency': [3, 5, 2, 1, 4, 2]
        })
        
        scatter = alt.Chart(placeholder_data).mark_circle(size=200).encode(
            x=alt.X('x:Q', scale=alt.Scale(domain=[-0.5, 2.5]), title='Field X Position'),
            y=alt.Y('y:Q', scale=alt.Scale(domain=[-0.5, 1.5]), title='Field Y Position'),
            size=alt.Size('frequency:Q', title='Frequency', scale=alt.Scale(range=[100, 1000])),
            color=alt.Color('frequency:Q', scale=alt.Scale(scheme='blues')),
            tooltip=['x', 'y', 'frequency']
        ).properties(
            width=500,
            height=300,
            title='Starting Position Heatmap (Placeholder)'
        )
        
        st.altair_chart(scatter, use_container_width=True)
    
    def match_predictor_tab(self):
        """Match Predictor tab implementation"""
        st.header("Match Predictor")
        st.markdown("Predict match outcomes based on team averages.")
        
        # Load data
        df = self.load_data()
        
        if df.empty:
            st.warning("No scouting data available. Please scan some QR codes first!")
            st.info("To get started, run `python3 scanner.py` and scan some scouting data QR codes.")
            return
        
        team_options = sorted(df['team_number'].tolist())
        
        if len(team_options) < 6:
            st.warning(f"Need at least 6 teams to predict a match. Currently have {len(team_options)} teams.")
            return
        
        st.markdown("---")
        
        # Alliance Selection
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Red Alliance")
            red_alliance = st.multiselect(
                "Select 3 teams for Red Alliance",
                options=team_options,
                max_selections=3,
                key="red_alliance",
                help="Select exactly 3 teams for the red alliance"
            )
        
        with col2:
            st.subheader("Blue Alliance")
            # Filter out teams already selected for red alliance
            blue_options = [t for t in team_options if t not in red_alliance]
            blue_alliance = st.multiselect(
                "Select 3 teams for Blue Alliance",
                options=blue_options,
                max_selections=3,
                key="blue_alliance",
                help="Select exactly 3 teams for the blue alliance"
            )
        
        # Only proceed if both alliances have exactly 3 teams
        if len(red_alliance) == 3 and len(blue_alliance) == 3:
            st.markdown("---")
            
            # Calculate alliance scores
            red_stats = df[df['team_number'].isin(red_alliance)]
            blue_stats = df[df['team_number'].isin(blue_alliance)]
            
            # Sum of averages
            red_auto = red_stats['Avg_Auto'].sum()
            red_teleop = red_stats['Avg_Teleop'].sum()
            red_total = red_auto + red_teleop
            
            blue_auto = blue_stats['Avg_Auto'].sum()
            blue_teleop = blue_stats['Avg_Teleop'].sum()
            blue_total = blue_auto + blue_teleop
            
            # Display team breakdowns
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Red Alliance Stats")
                for team in red_alliance:
                    team_data = df[df['team_number'] == team].iloc[0]
                    st.markdown(f"**Team {team}:** Auto: {team_data['Avg_Auto']:.2f}, Teleop: {team_data['Avg_Teleop']:.2f}")
                st.markdown(f"**Total Expected Score:** {red_total:.2f}")
            
            with col2:
                st.subheader("Blue Alliance Stats")
                for team in blue_alliance:
                    team_data = df[df['team_number'] == team].iloc[0]
                    st.markdown(f"**Team {team}:** Auto: {team_data['Avg_Auto']:.2f}, Teleop: {team_data['Avg_Teleop']:.2f}")
                st.markdown(f"**Total Expected Score:** {blue_total:.2f}")
            
            st.markdown("---")
            
            # Predicted Winner
            st.subheader("Prediction Results")
            
            total_score = red_total + blue_total
            EQUAL_PROBABILITY = 50.0
            if total_score > 0:
                red_probability = (red_total / total_score) * 100
                blue_probability = (blue_total / total_score) * 100
            else:
                red_probability = EQUAL_PROBABILITY
                blue_probability = EQUAL_PROBABILITY
            
            if red_total > blue_total:
                winner = "Red Alliance"
                winner_color = "[RED]"
                margin = red_total - blue_total
            elif blue_total > red_total:
                winner = "Blue Alliance"
                winner_color = "[BLUE]"
                margin = blue_total - red_total
            else:
                winner = "Tie"
                winner_color = ""
                margin = 0
            
            st.markdown(f"### {winner_color} Predicted Winner: **{winner}**")
            if margin > 0:
                st.markdown(f"Expected margin: **{margin:.2f} points**")
            
            st.markdown("---")
            
            # Win Probability Bar Chart
            st.subheader("Win Probability")
            
            prob_data = pd.DataFrame({
                'Alliance': ['Red Alliance', 'Blue Alliance'],
                'Probability': [red_probability, blue_probability],
                'Color': ['red', 'blue']
            })
            
            prob_chart = alt.Chart(prob_data).mark_bar().encode(
                x=alt.X('Probability:Q', title='Win Probability (%)', scale=alt.Scale(domain=[0, 100])),
                y=alt.Y('Alliance:N', title=''),
                color=alt.Color('Color:N', scale=alt.Scale(domain=['red', 'blue'], range=['#ff4444', '#4444ff']), legend=None),
                tooltip=['Alliance', alt.Tooltip('Probability:Q', format='.1f')]
            ).properties(
                width=600,
                height=200
            )
            
            st.altair_chart(prob_chart, use_container_width=True)
            
            # Display probabilities as metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Red Win Probability", f"{red_probability:.1f}%")
            with col2:
                st.metric("Blue Win Probability", f"{blue_probability:.1f}%")
        
        elif len(red_alliance) > 0 or len(blue_alliance) > 0:
            st.info("Please select exactly 3 teams for both alliances to see predictions.")
    
    def raw_data_tab(self):
        """Raw Data tab implementation"""
        st.header("Raw Data")
        st.markdown("View and download all scouting data from the database.")
        
        # Load raw data
        df = self.load_raw_data()
        
        if df.empty:
            st.warning("No scouting data available. Please scan some QR codes first!")
            st.info("To get started, run `python3 scanner.py` and scan some scouting data QR codes.")
            return
        
        # Display metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("Total Teams", df['team_number'].nunique())
        
        st.markdown("---")
        
        # Download CSV button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="scouting_data_export.csv",
            mime="text/csv",
            help="Download all scouting data as a CSV file"
        )
        
        st.markdown("---")
        
        # Display dataframe
        st.subheader("Sortable Data Table")
        st.markdown("Click on column headers to sort the data.")
        
        # Use st.dataframe for interactive sorting
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", help="Database record ID"),
                "timestamp": st.column_config.TextColumn("Timestamp"),
                "team_number": st.column_config.NumberColumn("Team #"),
                "scouter_name": st.column_config.TextColumn("Scouter"),
                "auto_balls_scored_upper": st.column_config.NumberColumn("Auto Upper"),
                "auto_balls_scored_lower": st.column_config.NumberColumn("Auto Lower"),
                "auto_taxi": st.column_config.NumberColumn("Auto Taxi"),
                "teleop_balls_scored_upper": st.column_config.NumberColumn("Teleop Upper"),
                "teleop_balls_scored_lower": st.column_config.NumberColumn("Teleop Lower"),
                "teleop_balls_missed": st.column_config.NumberColumn("Teleop Missed"),
                "climb_level": st.column_config.TextColumn("Climb Level"),
                "climb_time": st.column_config.NumberColumn("Climb Time"),
                "defense_rating": st.column_config.TextColumn("Defense"),
                "driver_skill": st.column_config.TextColumn("Driver Skill"),
                "penalties": st.column_config.NumberColumn("Penalties"),
                "broke_down": st.column_config.NumberColumn("Broke Down"),
                "notes": st.column_config.TextColumn("Notes"),
                "scanned_at": st.column_config.TextColumn("Scanned At")
            }
        )
    
    def manage_records_tab(self):
        """Manage Records tab implementation - Delete scouting records"""
        st.header("Manage Records")
        st.markdown("View and delete scouting records from the database.")
        
        # Load raw data
        df = self.load_raw_data()
        
        if df.empty:
            st.warning("No scouting data available.")
            return
        
        # Display metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("Total Teams", df['team_number'].nunique())
        
        st.markdown("---")
        
        # Filter options
        st.subheader("Filter Records")
        col1, col2 = st.columns(2)
        
        with col1:
            # Team filter
            team_options = ['All'] + sorted(df['team_number'].unique().tolist())
            selected_team = st.selectbox(
                "Filter by Team",
                options=team_options,
                help="Select a team to filter records"
            )
        
        with col2:
            # Scouter filter
            scouter_options = ['All'] + sorted(df['scouter_name'].unique().tolist())
            selected_scouter = st.selectbox(
                "Filter by Scouter",
                options=scouter_options,
                help="Select a scouter to filter records"
            )
        
        # Apply filters
        filtered_df = df.copy()
        if selected_team != 'All':
            filtered_df = filtered_df[filtered_df['team_number'] == selected_team]
        if selected_scouter != 'All':
            filtered_df = filtered_df[filtered_df['scouter_name'] == selected_scouter]
        
        st.markdown(f"**Showing {len(filtered_df)} of {len(df)} records**")
        st.markdown("---")
        
        # Display records with delete buttons
        st.subheader("Records")
        
        if filtered_df.empty:
            st.info("No records match the selected filters.")
        else:
            for idx, row in filtered_df.iterrows():
                col1, col2, col3 = st.columns([0.8, 3, 0.5])
                
                with col1:
                    st.markdown(f"**ID: {row['id']}**")
                
                with col2:
                    timestamp = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    auto_total = row['auto_balls_scored_upper'] + row['auto_balls_scored_lower']
                    teleop_total = row['teleop_balls_scored_upper'] + row['teleop_balls_scored_lower']
                    
                    st.markdown(
                        f"Team **{row['team_number']}** | "
                        f"Scouter: {row['scouter_name']} | "
                        f"Auto: {auto_total} | Teleop: {teleop_total} | "
                        f"Climb: {row['climb_level']} | "
                        f"{timestamp}"
                    )
                
                with col3:
                    if st.button("Delete", key=f"delete_{row['id']}"):
                        if self.delete_record(row['id']):
                            st.success(f"Record {row['id']} deleted!")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete record {row['id']}")
                
                st.markdown("---")
    
    def delete_record(self, record_id):
        """Delete a record from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM scouting_data WHERE id = ?', (record_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error deleting record: {e}")
            return False


def main():
    """Main entry point for Streamlit dashboard"""
    st.set_page_config(
        page_title="FRC Scouting Dashboard",
        page_icon="FRC",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("FRC Scouting Dashboard")
    
    dashboard = ScoutingDashboard()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pick List Formulation",
        "Team Analysis",
        "Match Predictor",
        "Raw Data",
        "Manage Records"
    ])
    
    with tab1:
        dashboard.pick_list_formulation_tab()
    
    with tab2:
        dashboard.team_analysis_tab()
    
    with tab3:
        dashboard.match_predictor_tab()
    
    with tab4:
        dashboard.raw_data_tab()
    
    with tab5:
        dashboard.manage_records_tab()


if __name__ == '__main__':
    main()
