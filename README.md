# farmart-backend

# Install PostgreSQL
Ensure PostgreSQL is installed on your machine. Set up a username and password if you haven't already.

# Connect PostgreSQL to DBeaver

Install DBeaver and connect it to your PostgreSQL instance using the username and password you configured.
Test the connection to confirm it’s working correctly.
Create Database Schema

Add or create the necessary tables for the project by executing the provided schema script in DBeaver.

## Working with Migrations
# Pull Latest Changes
Before making changes, pull the latest updates from the main branch to check for any new migrations.

# Apply Migrations
If there are new migrations, run the following command to upgrade your local database schema:
 <<flask db upgrade revision --autogenerate>>

