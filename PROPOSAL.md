# CSS 382 Capstone - UW Bothell Course Scheduler

## Project Proposal Summary

A web application where UW Bothell students describe their scheduling preferences in plain English and receive personalized, constraint-aware course recommendations down to the specific section.

## Problem

Students spend hours manually cross-referencing MyPlan, the Time Schedule, and degree requirements every quarter. Students with constraints like "I can't drive to campus on Fridays" or "I'm working 30 hours a week" have no intelligent tool to work with.

## Solution

A RAG-powered scheduling assistant that:
1. Scrapes live course data from UW Bothell's Time Schedule
2. Embeds course information into a vector store
3. Uses LLM reasoning to match student constraints with specific course sections
4. Returns conflict-free schedule recommendations

## Key Differentiator

**Section-level awareness** - Most planners surface courses. Ours surfaces schedules. Instead of recommending "CSS 342", we recommend "CSS 342 Section B (TTh 2:00–3:20pm)" based on the student's constraints.

## Team

- **Richie Chen** - Backend / Data Pipeline
- **Kevin Vo** - LLM / RAG Integration  
- **Yousuf Al-Bassyiouni** - Frontend / UX

## Technology Stack

- **Backend**: Python, FastAPI, OpenAI API, Pinecone
- **Frontend**: React, Axios
- **Data**: BeautifulSoup scraper, vector embeddings

## MVP Scope

- CSS core requirements only
- Spring 2026 data
- Day/time and credit constraints
- Prerequisite enforcement
- Schedule conflict detection
- Plain English query interface

## Success Criteria

- Zero schedule conflicts in 10 test queries
- No ineligible courses recommended
- Scraper uptime across 3 test runs
- ≥80% constraint extraction accuracy

## Status

✅ Initial project structure created with all core modules and components scaffolded
