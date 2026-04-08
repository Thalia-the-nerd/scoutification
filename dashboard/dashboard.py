#!/usr/bin/env python3
"""
FRC Scouting Dashboard — 2026 REBUILT
Streamlit dashboard for pick lists, team analysis, match prediction, and raw data.
"""

import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
import requests


class ScoutingDashboard:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv('DB_PATH', 'scouting_data.db')

    # ──────────────────────────────────────────────────────────────
    # Data Loaders
    # ──────────────────────────────────────────────────────────────

    def load_data(self):
        """Per-team aggregate stats for pick list / analysis."""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT
                team_number,
                COUNT(*) AS Matches_Played,

                AVG(auto_fuel_active_hub)  AS Avg_Auto_Fuel,
                AVG(CASE WHEN auto_tower_level1 = 1 THEN 1.0 ELSE 0.0 END) AS Auto_Tower_Rate,

                AVG(teleop_fuel_active_hub)   AS Avg_Teleop_Active,
                AVG(teleop_fuel_inactive_hub) AS Avg_Teleop_Inactive,
                AVG(auto_fuel_active_hub + teleop_fuel_active_hub) AS Avg_Total_Active_Hub,

                AVG(CASE max_tower_level
                    WHEN 'Level 3' THEN 3.0
                    WHEN 'Level 2' THEN 2.0
                    WHEN 'Level 1' THEN 1.0
                    ELSE 0.0
                END) AS Avg_Tower_Level,

                AVG(minor_fouls + major_fouls * 3) AS Avg_Foul_Points,

                AVG(CASE WHEN energized_rp    = 1 THEN 1.0 ELSE 0.0 END) AS Energized_Rate,
                AVG(CASE WHEN supercharged_rp = 1 THEN 1.0 ELSE 0.0 END) AS Supercharged_Rate,
                AVG(CASE WHEN traversal_rp    = 1 THEN 1.0 ELSE 0.0 END) AS Traversal_Rate
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
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(
                "SELECT * FROM scouting_data ORDER BY match_number, team_number", conn
            )
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading raw data: {e}")
            return pd.DataFrame()

    def load_team_match_data(self, team_number):
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT
                match_number,
                auto_fuel_active_hub,
                teleop_fuel_active_hub,
                teleop_fuel_inactive_hub,
                (auto_fuel_active_hub + teleop_fuel_active_hub) AS total_active_hub,
                CASE max_tower_level
                    WHEN 'Level 3' THEN 3
                    WHEN 'Level 2' THEN 2
                    WHEN 'Level 1' THEN 1
                    ELSE 0
                END AS tower_level_num,
                minor_fouls,
                major_fouls,
                shooter_cadence,
                shooter_accuracy,
                defensive_phase_summary,
                robot_photo
            FROM scouting_data
            WHERE team_number = ?
            ORDER BY match_number
            """
            df = pd.read_sql_query(query, conn, params=[team_number])
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error loading team data: {e}")
            return pd.DataFrame()

    def load_pre_scouting_data(self):
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("SELECT * FROM pre_scouting_data", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame()

    # ──────────────────────────────────────────────────────────────
    # Pick List Tab
    # ──────────────────────────────────────────────────────────────

    def pick_list_formulation_tab(self):
        st.header(" Pick List Formulation")
        st.markdown("Weighted team rankings for alliance selection.")

        df = self.load_data()
        if df.empty:
            st.warning("No scouting data yet. Scan some QR codes first!")
            return

        st.sidebar.header("️ Scoring Weights")

        auto_w     = st.sidebar.slider("Auto FUEL",          0.0, 5.0, 1.5, 0.1)
        teleop_w   = st.sidebar.slider("Teleop Active HUB",  0.0, 5.0, 2.0, 0.1)
        tower_w    = st.sidebar.slider("Tower Level",         0.0, 5.0, 1.5, 0.1)
        foul_w     = st.sidebar.slider("Foul Penalty (neg)",  0.0, 3.0, 1.0, 0.1)

        df['Weighted_Score'] = (
            df['Avg_Auto_Fuel']        * auto_w   +
            df['Avg_Teleop_Active']    * teleop_w +
            df['Avg_Tower_Level']      * tower_w  -
            df['Avg_Foul_Points']      * foul_w
        )

        df = df.sort_values('Weighted_Score', ascending=False).reset_index(drop=True)

        if 'dnp_teams' not in st.session_state:
            st.session_state.dnp_teams = set()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Teams Scouted", len(df))
        col2.metric("Energized RP% (avg)", f"{df['Energized_Rate'].mean()*100:.0f}%")
        col3.metric("Supercharged RP% (avg)", f"{df['Supercharged_Rate'].mean()*100:.0f}%")
        col4.metric("Traversal RP% (avg)", f"{df['Traversal_Rate'].mean()*100:.0f}%")

        st.markdown("---")
        st.subheader(" Team Rankings")

        # Header row
        hcols = st.columns([0.4, 0.4, 1.0, 0.9, 0.9, 0.9, 0.9, 0.9, 0.6])
        for col, label in zip(hcols, ["DNP","#","Team","Avg Auto","Avg Tel.act","Avg Tower","Fouls(pts)","Score","Matches"]):
            col.markdown(f"**{label}**")

        for idx, row in df.iterrows():
            team  = row['team_number']
            rank  = idx + 1
            emoji = "" if rank <= 8 else ("" if rank <= 24 else "")

            cols = st.columns([0.4, 0.4, 1.0, 0.9, 0.9, 0.9, 0.9, 0.9, 0.6])
            with cols[0]:
                is_dnp = st.checkbox("", value=team in st.session_state.dnp_teams,
                                     key=f"dnp_{team}_{idx}", help=f"DNP Team {team}")
                if is_dnp: st.session_state.dnp_teams.add(team)
                else:      st.session_state.dnp_teams.discard(team)
            cols[1].markdown(f"{emoji} **{rank}**")
            label_html = (f"<span style='text-decoration:line-through;color:gray'>Team {team}</span>"
                          if team in st.session_state.dnp_teams else f"**Team {team}**")
            cols[2].markdown(label_html, unsafe_allow_html=True)
            cols[3].text(f"{row['Avg_Auto_Fuel']:.1f}")
            cols[4].text(f"{row['Avg_Teleop_Active']:.1f}")
            cols[5].text(f"{row['Avg_Tower_Level']:.2f}")
            cols[6].text(f"{row['Avg_Foul_Points']:.1f}")
            cols[7].text(f"{row['Weighted_Score']:.2f}")
            cols[8].text(int(row['Matches_Played']))

        st.markdown("---")
        if st.button(" Export Pick List (excluding DNP)"):
            export = df[~df['team_number'].isin(st.session_state.dnp_teams)]
            st.download_button("Download CSV", export.to_csv(index=False),
                               "pick_list.csv", "text/csv")

    # ──────────────────────────────────────────────────────────────
    # Team Analysis Tab
    # ──────────────────────────────────────────────────────────────

    def team_analysis_tab(self):
        st.header(" Team Analysis")

        df = self.load_data()
        if df.empty:
            st.warning("No scouting data yet.")
            return

        team = st.sidebar.selectbox("Select Team",
                                    sorted(df['team_number'].tolist()))
        stats = df[df['team_number'] == team].iloc[0]

        st.subheader(f"Team {int(team)}")
        
        # Pull team metadata from Statbotics v3
        team_name, location, epa, world_rank = "Unknown Team", "Unknown Location", "N/A", "N/A"
        try:
            res = requests.get(f"https://api.statbotics.io/v3/team_year/{team}/2026", timeout=2)
            if res.status_code == 200:
                data = res.json()
                team_name = data.get('name', 'Unknown Team')
                location = f"{data.get('state', '')}, {data.get('country', '')}".strip(', ')
                
                epa_val = data.get('epa', {}).get('total_points', {}).get('mean', 0)
                if epa_val > 0:
                    epa = round(epa_val, 1)
                
                rank_val = data.get('epa', {}).get('ranks', {}).get('total', {}).get('rank', 0)
                if rank_val > 0:
                    world_rank = f"#{rank_val}"
        except Exception:
            pass
            
        st.markdown(f"**{team_name}** &nbsp;|&nbsp; 🌍 {location} &nbsp;|&nbsp; 🛡️ **2026 EPA:** {epa} &nbsp;|&nbsp; 🏆 **World Rank:** {world_rank}")
        st.markdown(f"**Matches manually scouted:** {int(stats['Matches_Played'])}")
        st.markdown("---")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Auto FUEL",      f"{stats['Avg_Auto_Fuel']:.1f}")
        c2.metric("Avg Teleop Active",   f"{stats['Avg_Teleop_Active']:.1f}")
        c3.metric("Avg Tower Level",     f"{stats['Avg_Tower_Level']:.2f}")
        c4.metric("Auto Tower Rate",     f"{stats['Auto_Tower_Rate']*100:.0f}%")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Avg Teleop Inactive", f"{stats['Avg_Teleop_Inactive']:.1f}")
        c6.metric("Energized RP%",       f"{stats['Energized_Rate']*100:.0f}%")
        c7.metric("Supercharged RP%",    f"{stats['Supercharged_Rate']*100:.0f}%")
        c8.metric("Traversal RP%",       f"{stats['Traversal_Rate']*100:.0f}%")

        st.markdown("---")
        
        # Load Pre-scouting data
        pre_scout_df = self.load_pre_scouting_data()
        pre_stats = None
        if not pre_scout_df.empty and team in pre_scout_df['team_number'].values:
            pre_stats = pre_scout_df[pre_scout_df['team_number'] == team].iloc[0]

        match_data = self.load_team_match_data(team)
        
        st.subheader("️ Hardware & Strategy (Pre-Scouting & Latest Match)")
        p1, p2, p3 = st.columns(3)
        if pre_stats is not None:
            p1.metric("Drive System", pre_stats.get('drive_system', 'N/A'))
            p2.metric("Has Turret", pre_stats.get('has_turret', 'N/A'))
            fuel_cap = pre_stats.get('fuel_capacity', '0')
            if pd.isna(fuel_cap): fuel_cap = 0
            p3.metric("FUEL Capacity", f"{int(fuel_cap)}")
        else:
            p1.info("No Pre-Scouting data available.")
        
        if not match_data.empty:
            latest_match = match_data.iloc[-1]
            p4, p5, p6 = st.columns(3)
            p4.metric("Shooter Cadence (Latest)", latest_match.get('shooter_cadence', 'N/A'))
            p5.metric("Shooter Accuracy (Latest)", latest_match.get('shooter_accuracy', 'N/A'))
            p6.metric("Defensive Phase (Latest)", latest_match.get('defensive_phase_summary', 'N/A'))

        if pre_stats is not None and pre_stats.get('robot_photo') is not None:
            photo_bytes = pre_stats['robot_photo']
            if isinstance(photo_bytes, bytes):
                st.image(photo_bytes, caption=f"Team {team} Robot (Pit Photo)", use_container_width=True)

        if not match_data.empty:
            st.subheader(" FUEL Scored Per Match")
            melted = match_data[['match_number', 'auto_fuel_active_hub',
                                  'teleop_fuel_active_hub', 'teleop_fuel_inactive_hub']].melt(
                id_vars='match_number', var_name='Period', value_name='FUEL'
            )
            melted['Period'] = melted['Period'].map({
                'auto_fuel_active_hub':    'Auto (Active HUB)',
                'teleop_fuel_active_hub':  'Teleop (Active HUB)',
                'teleop_fuel_inactive_hub':'Teleop (Inactive HUB)',
            })
            chart = alt.Chart(melted).mark_line(point=True).encode(
                x=alt.X('match_number:Q', title='Match'),
                y=alt.Y('FUEL:Q', title='FUEL Scored'),
                color=alt.Color('Period:N'),
                tooltip=['match_number', 'Period', 'FUEL']
            ).properties(height=350).interactive()
            st.altair_chart(chart, use_container_width=True)

            st.subheader("️ TOWER Level Per Match")
            tower_chart = alt.Chart(match_data).mark_bar().encode(
                x=alt.X('match_number:Q', title='Match'),
                y=alt.Y('tower_level_num:Q', title='Tower Level', scale=alt.Scale(domain=[0, 3])),
                color=alt.Color('tower_level_num:Q', scale=alt.Scale(scheme='blues')),
                tooltip=['match_number', 'tower_level_num']
            ).properties(height=200)
            st.altair_chart(tower_chart, use_container_width=True)

    # ──────────────────────────────────────────────────────────────
    # Match Predictor Tab
    # ──────────────────────────────────────────────────────────────

    def match_predictor_tab(self):
        st.header(" Match Predictor")
        st.markdown("Predicts match outcome based on scouted team averages.")

        df = self.load_data()
        if df.empty:
            st.warning("No scouting data yet.")
            return

        teams = sorted(df['team_number'].tolist())
        if len(teams) < 6:
            st.warning(f"Need at least 6 scouted teams. Have {len(teams)}.")
            return

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(" Red Alliance")
            red = st.multiselect("Red teams", teams, max_selections=3, key="red")
        with col2:
            st.subheader(" Blue Alliance")
            blue = st.multiselect("Blue teams", [t for t in teams if t not in red],
                                  max_selections=3, key="blue")

        if len(red) == 3 and len(blue) == 3:
            st.markdown("---")

            def alliance_score(team_list):
                rows = df[df['team_number'].isin(team_list)]
                active_hub  = rows['Avg_Total_Active_Hub'].sum()
                tower       = rows['Avg_Tower_Level'].sum()
                fouls       = rows['Avg_Foul_Points'].sum()
                # Rough REBUILT scoring: active hub FUEL + tower contributions
                score = active_hub + (tower * 15) - fouls
                return score, active_hub, tower, fouls

            r_score, r_hub, r_tower, r_fouls = alliance_score(red)
            b_score, b_hub, b_tower, b_fouls = alliance_score(blue)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader(" Red")
                for t in red:
                    row = df[df['team_number'] == t].iloc[0]
                    st.markdown(f"**{int(t)}:** Active HUB avg {row['Avg_Total_Active_Hub']:.1f}, "
                                f"Tower {row['Avg_Tower_Level']:.1f}")
                st.metric("Expected Score", f"{r_score:.1f}")
                st.metric("Avg Active HUB FUEL", f"{r_hub:.0f}")
                energized  = "" if r_hub >= 100 else ""
                supercharged = "" if r_hub >= 360 else ""
                st.markdown(f"ENERGIZED RP likely: {energized} &nbsp; SUPERCHARGED RP likely: {supercharged}")
            with col2:
                st.subheader(" Blue")
                for t in blue:
                    row = df[df['team_number'] == t].iloc[0]
                    st.markdown(f"**{int(t)}:** Active HUB avg {row['Avg_Total_Active_Hub']:.1f}, "
                                f"Tower {row['Avg_Tower_Level']:.1f}")
                st.metric("Expected Score", f"{b_score:.1f}")
                st.metric("Avg Active HUB FUEL", f"{b_hub:.0f}")
                energized  = "" if b_hub >= 100 else ""
                supercharged = "" if b_hub >= 360 else ""
                st.markdown(f"ENERGIZED RP likely: {energized} &nbsp; SUPERCHARGED RP likely: {supercharged}")

            st.markdown("---")
            total = r_score + b_score
            r_pct = (r_score / total * 100) if total > 0 else 50
            b_pct = 100 - r_pct

            winner = " Red Alliance" if r_score > b_score else (" Blue Alliance" if b_score > r_score else " Tie")
            st.subheader(f" {winner}")

            prob = pd.DataFrame({'Alliance': ['Red', 'Blue'], 'Probability': [r_pct, b_pct], 'Color': ['red', 'blue']})
            st.altair_chart(
                alt.Chart(prob).mark_bar().encode(
                    x=alt.X('Probability:Q', scale=alt.Scale(domain=[0, 100]), title='Win Probability (%)'),
                    y=alt.Y('Alliance:N', title=''),
                    color=alt.Color('Color:N', scale=alt.Scale(domain=['red','blue'], range=['#ff4444','#4444ff']), legend=None),
                    tooltip=['Alliance', alt.Tooltip('Probability:Q', format='.1f')]
                ).properties(height=150),
                use_container_width=True
            )
        elif red or blue:
            st.info("Select exactly 3 teams per alliance.")

    # ──────────────────────────────────────────────────────────────
    # Raw Data Tab
    # ──────────────────────────────────────────────────────────────

    def raw_data_tab(self):
        st.header(" Raw Data")
        df = self.load_raw_data()
        if df.empty:
            st.warning("No scouting data yet.")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("Records", len(df))
        c2.metric("Teams",   df['team_number'].nunique())
        c3.metric("Matches", df['match_number'].nunique())

        st.markdown("---")
        st.download_button(" Download CSV", df.to_csv(index=False),
                           "scouting_data_rebuilt_2026.csv", "text/csv")
        st.markdown("---")
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "match_number":             st.column_config.NumberColumn("Match #"),
                         "team_number":              st.column_config.NumberColumn("Team #"),
                         "alliance":                 st.column_config.TextColumn("Alliance"),
                         "scouter_name":             st.column_config.TextColumn("Scouter"),
                         "pre_loaded_fuel":          st.column_config.NumberColumn("Pre-load"),
                         "auto_fuel_active_hub":     st.column_config.NumberColumn("Auto Fuel"),
                         "auto_tower_level1":        st.column_config.NumberColumn("Auto Twr L1"),
                         "teleop_fuel_active_hub":   st.column_config.NumberColumn("TP Active"),
                         "teleop_fuel_inactive_hub": st.column_config.NumberColumn("TP Inactive"),
                         "fuel_collection_source":   st.column_config.TextColumn("Collection"),
                         "max_tower_level":          st.column_config.TextColumn("Tower"),
                         "minor_fouls":              st.column_config.NumberColumn("Minor Fouls"),
                         "major_fouls":              st.column_config.NumberColumn("Major Fouls"),
                         "energized_rp":             st.column_config.NumberColumn("Energized"),
                         "supercharged_rp":          st.column_config.NumberColumn("Supercharged"),
                         "traversal_rp":             st.column_config.NumberColumn("Traversal"),
                     })

    # ──────────────────────────────────────────────────────────────
    # Match Preview (TBA & Statbotics)
    # ──────────────────────────────────────────────────────────────

    def match_preview_tab(self):
        st.header(" Match Preview & Strategy")
        st.markdown("Fetch upcoming matches from The Blue Alliance to view EPAs and Scouting Data.")
        
        c1, c2, c3 = st.columns(3)
        DEFAULT_API_KEY = "OZRrMZT1z5Qs0G2vPPZKCNWFC1QZHrOCYRwq2Fr3cRFc41gIfbgqh0YlCaJSdrRF"
        tba_key = c1.text_input("TBA Event Key", value="2026flwp", help="Find your event key on bluealliance.com (e.g., 2026flwp)")
        match_num = c2.number_input("Qual Match Number", min_value=1, value=1)
        api_key = c3.text_input("TBA API Key", type="password", value=DEFAULT_API_KEY, help="Required for live TBA sync. Get one at thebluealliance.com/account")
        
        if st.button("Load Preview", type="primary"):
            if not tba_key:
                st.error("Event key is required.")
                return
                
            with st.spinner("Fetching TBA and Statbotics data..."):
                headers = {"X-TBA-Auth-Key": api_key} if api_key else {}
                url = f"https://www.thebluealliance.com/api/v3/match/{tba_key}_qm{match_num}"
                
                red_teams = []
                blue_teams = []
                
                try:
                    resp = requests.get(url, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        red_teams = [int(t.replace('frc','')) for t in data['alliances']['red']['team_keys']]
                        blue_teams = [int(t.replace('frc','')) for t in data['alliances']['blue']['team_keys']]
                        st.success(f"✓ Synced Match {match_num} from TBA")
                    elif resp.status_code == 401:
                        st.error("TBA Error 401: Unauthorized. Your API Key is invalid or missing.")
                    elif resp.status_code == 404:
                        st.error(f"TBA Error 404: Match {match_num} not found. The schedule for {tba_key} might not be published yet!")
                    else:
                        st.warning(f"TBA sync failed (Status {resp.status_code}).")
                except Exception as e:
                    st.warning(f"TBA connection error: {e}")
                
                # Manual Override Checkbox (Persist in session state)
                if not red_teams or not blue_teams:
                    st.info("💡 You can manually enter the teams below since the TBA sync failed.")
                    
                    c1, c2 = st.columns(2)
                    m1, m2, m3 = c1.columns(3)
                    red_teams = [
                        m1.number_input("Red 1", min_value=1, value=254, key="r1"),
                        m2.number_input("Red 2", min_value=1, value=1678, key="r2"),
                        m3.number_input("Red 3", min_value=1, value=1323, key="r3")
                    ]
                    
                    b1, b2, b3 = c2.columns(3)
                    blue_teams = [
                        b1.number_input("Blue 1", min_value=1, value=2056, key="b1"),
                        b2.number_input("Blue 2", min_value=1, value=118, key="b2"),
                        b3.number_input("Blue 3", min_value=1, value=148, key="b3")
                    ]
                    
                self._render_match_preview(red_teams, blue_teams)

    def _render_match_preview(self, red_teams, blue_teams):
        st.markdown("---")
        df = self.load_data()
        pre_df = self.load_pre_scouting_data()

        col1, col2 = st.columns(2)
        with col1:
            st.error("🟥 RED ALLIANCE")
            for t in red_teams:
                st.markdown(f"<div style='background-color:#4a1212;padding:12px;border-radius:8px;border-left:6px solid #ff4444;color:white;margin-bottom:12px;font-size:1.1em;'>{self._html_card(t, df, pre_df)}</div>", unsafe_allow_html=True)
                
        with col2:
            st.info("🟦 BLUE ALLIANCE")
            for t in blue_teams:
                st.markdown(f"<div style='background-color:#121a4a;padding:12px;border-radius:8px;border-left:6px solid #4444ff;color:white;margin-bottom:12px;font-size:1.1em;'>{self._html_card(t, df, pre_df)}</div>", unsafe_allow_html=True)

    def _html_card(self, t, df, pre_df):
        epa = "N/A"
        try:
            # Try Statbotics v3 (current 2026)
            res = requests.get(f"https://api.statbotics.io/v3/team_year/{t}/2026", timeout=2)
            if res.status_code == 200:
                data = res.json()
                # v3 structure: epa['total_points']['mean']
                epa_val = data.get('epa', {}).get('total_points', {}).get('mean', 0)
                if epa_val > 0:
                    epa = round(epa_val, 1)
                else:
                    # Fallback to 2025 EPA if 2026 is zero/new
                    res2 = requests.get(f"https://api.statbotics.io/v3/team_year/{t}/2025", timeout=2)
                    if res2.status_code == 200:
                        epa_val2 = res2.json().get('epa', {}).get('total_points', {}).get('mean', 0)
                        if epa_val2 > 0:
                            epa = f"{round(epa_val2, 1)} (2025)"
        except Exception:
            pass
            
        scout = df[df['team_number'] == t].iloc[0] if (not df.empty and t in df['team_number'].values) else None
        pit = pre_df[pre_df['team_number'] == t].iloc[0] if (not pre_df.empty and t in pre_df['team_number'].values) else None
        
        drive = pit['drive_system'] if pit is not None and not pd.isna(pit['drive_system']) else 'Not Scouted'
        trench = pit['can_traverse_trench'] if pit is not None and not pd.isna(pit['can_traverse_trench']) else 'Not Scouted'
        
        avg_hub = f"{scout['Avg_Total_Active_Hub']:.1f}" if scout is not None else '?'
        avg_twr = f"{scout['Avg_Tower_Level']:.1f}" if scout is not None else '?'
        
        status_note = ""
        if scout is None:
            status_note = "<br><i style='color:#f8d7da;font-size:0.8em;'>Note: No match data collected yet for this team.</i>"
        
        return f"<b style='font-size:1.3em;'>Team {t}</b> <span style='float:right;color:#aaa;'>EPA: {epa}</span><br><br><b>Avg Scored:</b> {avg_hub} HUB | Tower Lvl {avg_twr}<br><b>Drive:</b> {drive} | <b>Under Trench:</b> {trench}{status_note}"


    # ──────────────────────────────────────────────────────────────
    # Assignments Portal & Tracker Tab
    # ──────────────────────────────────────────────────────────────

    def assignments_tab(self):
        st.header("🎛️ Assignments Portal")
        st.markdown("Assign teams and matches to scouters, and track their performance.")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Add Scouter")
            new_scouter = st.text_input("Scouter Name")
            if st.button("Add Scouter", type="primary"):
                if new_scouter:
                    try:
                        conn = sqlite3.connect(self.db_path)
                        conn.execute('INSERT OR IGNORE INTO scouters (name) VALUES (?)', (new_scouter.strip().lower(),))
                        conn.commit()
                        conn.close()
                        st.success(f"Added scouter: {new_scouter.strip().lower()}")
                    except Exception as e:
                        st.error(f"Error adding scouter: {e}")

        with col2:
            st.subheader("Assign Team")
            try:
                conn = sqlite3.connect(self.db_path)
                # Create tables if they don't exist yet just in case
                conn.execute('''CREATE TABLE IF NOT EXISTS scouters (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)''')
                conn.execute('''CREATE TABLE IF NOT EXISTS scouter_assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, scouter_name TEXT NOT NULL, match_number INTEGER NOT NULL, team_number INTEGER NOT NULL, UNIQUE(match_number, team_number))''')
                scouters = [row[0] for row in conn.execute('SELECT name FROM scouters ORDER BY name').fetchall()]
                conn.close()
            except:
                scouters = []

            if not scouters:
                st.info("No scouters added yet. Add one on the left.")
            else:
                a_scouter = st.selectbox("Scouter", scouters)
                c_match, c_team = st.columns(2)
                a_match = c_match.number_input("Match Number", min_value=1, value=1)
                a_team = c_team.number_input("Team Number", min_value=1, value=1)
                if st.button("Assign"):
                    try:
                        conn = sqlite3.connect(self.db_path)
                        conn.execute('INSERT OR REPLACE INTO scouter_assignments (scouter_name, match_number, team_number) VALUES (?, ?, ?)',
                                     (a_scouter, a_match, a_team))
                        conn.commit()
                        conn.close()
                        st.success(f"Assigned Match {a_match}, Team {a_team} to {a_scouter}")
                    except Exception as e:
                        st.error(f"Error assigning: {e}")

        st.markdown("---")
        st.subheader("Scouter Performance & Assignments")
        
        try:
            conn = sqlite3.connect(self.db_path)
            assignments_query = """
                SELECT a.scouter_name, a.match_number, a.team_number,
                       CASE WHEN s.id IS NOT NULL THEN '✅ Completed' ELSE '❌ Pending' END AS status
                FROM scouter_assignments a
                LEFT JOIN scouting_data s ON a.match_number = s.match_number AND a.team_number = s.team_number AND a.scouter_name = s.scouter_name
                ORDER BY a.match_number, a.team_number
            """
            a_df = pd.read_sql_query(assignments_query, conn)
            conn.close()
            
            if not a_df.empty:
                st.dataframe(a_df, use_container_width=True, hide_index=True)
                
                st.write("**Completion Rates:**")
                completion = a_df.groupby('scouter_name')['status'].apply(lambda x: (x == '✅ Completed').mean() * 100).reset_index()
                completion.columns = ['Scouter', 'Completion %']
                completion['Completion %'] = completion['Completion %'].round(1)
                st.dataframe(completion, use_container_width=True, hide_index=True)
            else:
                st.info("No assignments yet.")
                
        except Exception as e:
            st.error(f"Error loading assignments: {e}")

def main():
    st.set_page_config(
        page_title="FRC Scouting – REBUILT 2026",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("FRC Scouting Dashboard — REBUILT 2026")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("✨ **Made by Thalia**")

    dash = ScoutingDashboard()
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Pick List", "Team Analysis", "Match Predictor", "Match Preview", "Raw Data", "Assignments"
    ])
    with tab1: dash.pick_list_formulation_tab()
    with tab2: dash.team_analysis_tab()
    with tab3: dash.match_predictor_tab()
    with tab4: dash.match_preview_tab()
    with tab5: dash.raw_data_tab()
    with tab6: dash.assignments_tab()


if __name__ == '__main__':
    main()
