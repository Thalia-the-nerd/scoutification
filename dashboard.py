#!/usr/bin/env python3
"""
FRC Scouting System - Streamlit Dashboard
Interactive dashboard for analyzing scouting data
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Database connection
DB_PATH = 'scouting_data.db'

# Constants
CLIMB_LEVELS = ('Low', 'Mid', 'High', 'Traversal')


@st.cache_data
def get_all_data():
    """Fetch all data from the database"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM scouting_data ORDER BY match_number, team_number"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data
def get_team_stats(team_number):
    """
    Get statistics for a specific team
    Handles cases where team has zero matches by returning None
    """
    conn = sqlite3.connect(DB_PATH)
    
    # Check if team exists and has data
    check_query = "SELECT COUNT(*) as count FROM scouting_data WHERE team_number = ?"
    count_df = pd.read_sql_query(check_query, conn, params=(team_number,))
    
    if count_df['count'].iloc[0] == 0:
        conn.close()
        return None
    
    # Get team statistics
    query = """
        SELECT 
            match_number,
            team_number,
            alliance,
            (auto_balls_scored_upper + auto_balls_scored_lower) as auto_score,
            (teleop_balls_scored_upper + teleop_balls_scored_lower) as teleop_score,
            climb_level,
            CASE 
                WHEN climb_level IN {climb_levels} THEN 1 
                ELSE 0 
            END as climbed
        FROM scouting_data 
        WHERE team_number = ?
        ORDER BY match_number
    """.format(climb_levels=CLIMB_LEVELS)
    df = pd.read_sql_query(query, conn, params=(team_number,))
    conn.close()
    return df


@st.cache_data
def get_team_list():
    """Get list of all teams in the database"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT DISTINCT team_number FROM scouting_data ORDER BY team_number"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df['team_number'].tolist()


@st.cache_data
def get_team_averages(team_number):
    """
    Calculate average statistics for a team
    Returns None if team has zero matches
    """
    conn = sqlite3.connect(DB_PATH)
    
    # Check if team exists
    check_query = "SELECT COUNT(*) as count FROM scouting_data WHERE team_number = ?"
    count_df = pd.read_sql_query(check_query, conn, params=(team_number,))
    
    if count_df['count'].iloc[0] == 0:
        conn.close()
        return None
    
    query = """
        SELECT 
            AVG(auto_balls_scored_upper + auto_balls_scored_lower) as avg_auto,
            AVG(teleop_balls_scored_upper + teleop_balls_scored_lower) as avg_teleop,
            AVG(CASE 
                WHEN climb_level IN {climb_levels} THEN 1.0 
                ELSE 0.0 
            END) * 100 as climb_pct
        FROM scouting_data 
        WHERE team_number = ?
    """.format(climb_levels=CLIMB_LEVELS)
    df = pd.read_sql_query(query, conn, params=(team_number,))
    conn.close()
    return df.iloc[0] if not df.empty else None


def team_analysis_tab():
    """Team Analysis Tab"""
    st.header("Team Analysis")
    
    # Get list of teams
    teams = get_team_list()
    
    if not teams:
        st.warning("No teams found in the database. Please scan some QR codes first.")
        return
    
    # Sidebar for team selection
    st.sidebar.header("Team Selection")
    selected_team = st.sidebar.selectbox(
        "Select Team Number",
        options=teams,
        index=0
    )
    
    # Get team data
    team_stats = get_team_stats(selected_team)
    team_averages = get_team_averages(selected_team)
    
    if team_stats is None or team_averages is None:
        st.error(f"No data found for Team {selected_team}")
        return
    
    # Display team header
    st.subheader(f"Team {selected_team} Performance")
    
    # Metric Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Avg Auto Score",
            value=f"{team_averages['avg_auto']:.2f}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Avg Teleop Score",
            value=f"{team_averages['avg_teleop']:.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="Climb %",
            value=f"{team_averages['climb_pct']:.1f}%",
            delta=None
        )
    
    # Line Chart: Score evolution over match numbers
    st.subheader("Score Evolution")
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=team_stats['match_number'],
        y=team_stats['auto_score'],
        mode='lines+markers',
        name='Auto Score',
        line=dict(color='blue', width=2),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=team_stats['match_number'],
        y=team_stats['teleop_score'],
        mode='lines+markers',
        name='Teleop Score',
        line=dict(color='red', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=f"Team {selected_team} - Score Evolution",
        xaxis_title="Match Number",
        yaxis_title="Score",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap Placeholder: Starting positions scatter plot
    st.subheader("Starting Positions Heatmap")
    
    # Since the database doesn't have starting position data, create a placeholder
    st.info("Starting position data not available in current database schema. "
            "This would show a scatter plot of robot starting positions on the field.")
    
    # Create a simple placeholder visualization
    # If we had x, y coordinates, we would plot them here
    # For now, show alliance distribution
    alliance_counts = team_stats['alliance'].value_counts()
    
    fig_alliance = px.bar(
        x=alliance_counts.index,
        y=alliance_counts.values,
        labels={'x': 'Alliance', 'y': 'Number of Matches'},
        title=f"Team {selected_team} - Alliance Distribution",
        color=alliance_counts.index,
        color_discrete_map={'Red': '#FF0000', 'Blue': '#0000FF'}
    )
    
    st.plotly_chart(fig_alliance, use_container_width=True)
    
    # Show match details
    st.subheader("Match Details")
    st.dataframe(
        team_stats[['match_number', 'alliance', 'auto_score', 'teleop_score', 'climb_level']],
        use_container_width=True,
        hide_index=True
    )


def match_predictor_tab():
    """Match Predictor Tab"""
    st.header("Match Predictor")
    
    # Get list of teams
    teams = get_team_list()
    
    if not teams:
        st.warning("No teams found in the database. Please scan some QR codes first.")
        return
    
    # Alliance selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔴 Red Alliance")
        red_alliance = st.multiselect(
            "Select 3 teams for Red Alliance",
            options=teams,
            max_selections=3,
            key="red_alliance"
        )
    
    with col2:
        st.subheader("🔵 Blue Alliance")
        blue_alliance = st.multiselect(
            "Select 3 teams for Blue Alliance",
            options=teams,
            max_selections=3,
            key="blue_alliance"
        )
    
    # Validate selections
    if len(red_alliance) == 3 and len(blue_alliance) == 3:
        # Calculate alliance scores
        red_auto_total = 0
        red_teleop_total = 0
        blue_auto_total = 0
        blue_teleop_total = 0
        
        # Red alliance averages
        for team in red_alliance:
            averages = get_team_averages(team)
            if averages is not None:
                red_auto_total += averages['avg_auto']
                red_teleop_total += averages['avg_teleop']
        
        # Blue alliance averages
        for team in blue_alliance:
            averages = get_team_averages(team)
            if averages is not None:
                blue_auto_total += averages['avg_auto']
                blue_teleop_total += averages['avg_teleop']
        
        # Calculate total predicted scores
        red_total = red_auto_total + red_teleop_total
        blue_total = blue_auto_total + blue_teleop_total
        
        # Display predictions
        st.subheader("Prediction Results")
        
        # Score comparison
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col1:
            st.metric(
                label="Red Alliance Predicted Score",
                value=f"{red_total:.2f}",
                delta=None
            )
            st.write(f"Auto: {red_auto_total:.2f}")
            st.write(f"Teleop: {red_teleop_total:.2f}")
        
        with col2:
            st.markdown("### VS")
        
        with col3:
            st.metric(
                label="Blue Alliance Predicted Score",
                value=f"{blue_total:.2f}",
                delta=None
            )
            st.write(f"Auto: {blue_auto_total:.2f}")
            st.write(f"Teleop: {blue_teleop_total:.2f}")
        
        # Predicted Winner
        st.markdown("---")
        
        if red_total > blue_total:
            winner = "Red Alliance"
            winner_color = "red"
            margin = red_total - blue_total
        elif blue_total > red_total:
            winner = "Blue Alliance"
            winner_color = "blue"
            margin = blue_total - red_total
        else:
            winner = "Tie"
            winner_color = "gray"
            margin = 0
        
        st.markdown(f"### 🏆 Predicted Winner: **:{winner_color}[{winner}]**")
        if margin > 0:
            st.write(f"Predicted margin: {margin:.2f} points")
        
        # Win Probability Bar Chart
        st.subheader("Win Probability")
        
        # Calculate win probability (simple ratio-based)
        total_score = red_total + blue_total
        if total_score > 0:
            red_prob = (red_total / total_score) * 100
            blue_prob = (blue_total / total_score) * 100
        else:
            red_prob = 50
            blue_prob = 50
        
        # Create probability bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=['Probability'],
            x=[red_prob],
            name='Red Alliance',
            orientation='h',
            marker=dict(color='red'),
            text=[f"{red_prob:.1f}%"],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            y=['Probability'],
            x=[blue_prob],
            name='Blue Alliance',
            orientation='h',
            marker=dict(color='blue'),
            text=[f"{blue_prob:.1f}%"],
            textposition='inside'
        ))
        
        fig.update_layout(
            barmode='stack',
            height=200,
            showlegend=True,
            xaxis=dict(range=[0, 100], title="Win Probability (%)"),
            yaxis=dict(showticklabels=False)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed breakdown
        with st.expander("📊 Detailed Breakdown"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Red Alliance Teams:**")
                for team in red_alliance:
                    averages = get_team_averages(team)
                    if averages is not None:
                        st.write(f"Team {team}: {averages['avg_auto'] + averages['avg_teleop']:.2f} pts avg")
            
            with col2:
                st.markdown("**Blue Alliance Teams:**")
                for team in blue_alliance:
                    averages = get_team_averages(team)
                    if averages is not None:
                        st.write(f"Team {team}: {averages['avg_auto'] + averages['avg_teleop']:.2f} pts avg")
    
    else:
        st.info("Please select exactly 3 teams for each alliance to see predictions.")


def raw_data_tab():
    """Raw Data Tab"""
    st.header("Raw Data")
    
    # Get all data
    df = get_all_data()
    
    if df.empty:
        st.warning("No data found in the database. Please scan some QR codes first.")
        return
    
    # Display number of records
    st.write(f"Total records: {len(df)}")
    
    # Sortable dataframe
    st.subheader("Scouting Data")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
    
    # Download CSV button
    st.subheader("Export Data")
    
    csv = df.to_csv(index=False)
    
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="scouting_data.csv",
        mime="text/csv",
        help="Download the complete dataset as a CSV file"
    )
    
    # Basic statistics
    with st.expander("📊 Quick Statistics"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Matches", df['match_number'].nunique())
        
        with col2:
            st.metric("Total Teams", df['team_number'].nunique())
        
        with col3:
            st.metric("Total Records", len(df))


def main():
    """Main dashboard application"""
    st.set_page_config(
        page_title="FRC Scouting Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🤖 FRC Scouting System Dashboard")
    st.markdown("---")
    
    # Check if database exists
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.close()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        st.info("Please ensure scouting_data.db exists in the current directory.")
        return
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Team Analysis", "Match Predictor", "Raw Data"])
    
    with tab1:
        team_analysis_tab()
    
    with tab2:
        match_predictor_tab()
    
    with tab3:
        raw_data_tab()
    
    # Footer
    st.markdown("---")
    st.markdown("*FRC Scouting System - Built with Streamlit*")


if __name__ == "__main__":
    main()
