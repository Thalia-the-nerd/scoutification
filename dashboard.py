#!/usr/bin/env python3
"""
FRC Scouting System - Data Analysis Dashboard
Streamlit dashboard for analyzing scouting data and creating pick lists
"""

import streamlit as st
import pandas as pd
import sqlite3
import numpy as np


class ScoutingDashboard:
    def __init__(self, db_path='scouting_data.db'):
        self.db_path = db_path
    
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
    
    def pick_list_formulation_tab(self):
        """Pick List Formulation tab implementation"""
        st.header("🎯 Pick List Formulation")
        st.markdown("Calculate weighted scores for teams and identify top picks.")
        
        # Load data
        df = self.load_data()
        
        if df.empty:
            st.warning("No scouting data available. Please scan some QR codes first!")
            st.info("To get started, run `python3 scanner.py` and scan some scouting data QR codes.")
            return
        
        # Sidebar - Weight Sliders
        st.sidebar.header("⚖️ Weight Configuration")
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
        
        st.subheader("📊 Team Rankings")
        
        # Create interactive table with DNP checkboxes
        for idx, row in display_df.iterrows():
            team = row['Team']
            rank = row['Rank']
            
            # Determine highlight color
            if rank <= 8:
                highlight = "🥇"  # Gold - First Pick
                color = "#FFD700"
            elif rank <= 24:
                highlight = "🥈"  # Silver - Second Pick
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
            st.markdown("🥇 <span style='background-color: #FFD700; padding: 5px; border-radius: 3px;'>**Gold (Top 8)**</span> - First Pick Candidates", unsafe_allow_html=True)
        with col2:
            st.markdown("🥈 <span style='background-color: #C0C0C0; padding: 5px; border-radius: 3px;'>**Silver (9-24)**</span> - Second Pick Candidates", unsafe_allow_html=True)
        
        # Export filtered pick list
        st.markdown("---")
        if st.button("📥 Export Pick List (Excluding DNP)"):
            export_df = display_df[~display_df['Team'].isin(st.session_state.dnp_teams)]
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="Download Pick List CSV",
                data=csv,
                file_name="pick_list.csv",
                mime="text/csv"
            )
            st.success("Pick list ready for download!")


def main():
    """Main entry point for Streamlit dashboard"""
    st.set_page_config(
        page_title="FRC Scouting Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🤖 FRC Scouting Dashboard")
    
    dashboard = ScoutingDashboard()
    
    # Create tabs
    tab1 = st.tabs(["Pick List Formulation"])[0]
    
    with tab1:
        dashboard.pick_list_formulation_tab()


if __name__ == '__main__':
    main()
