# Automated Brand Design System

This repository contains a specialized AI-driven pipeline. The system automates the creation of brand-cohesive header imagery by scraping live blog content and applying a two-stage generative workflow.

## Quick Start

### 1. Prerequisites
* Python 3.10 or higher
* Conda (recommended)

### 2. Installation & Setup
# Create and activate environment
conda create -n env python=3.11 -y
conda activate env

# Install dependencies
pip install streamlit requests beautifulsoup4 Pillow

# API Setup
Create the folder ".streamlit" and add Openrouter API key in a secrets.toml file
