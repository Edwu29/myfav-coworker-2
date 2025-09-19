# Database Schema

## Table: `myfav-coworker-main`
* **Primary Key Schema**:
    * **Partition Key (PK)**: A composite key to uniquely identify an item (e.g., `USER#{github_id}` or `JOB#{job_id}`).
    * **Sort Key (SK)**: For this simple schema, we'll use a static value like `METADATA` for the main record.
* **Item Structures**: JSON structures for User and SimulationJob items are defined.
* **Secondary Indexes**: A Global Secondary Index (GSI) is defined to query jobs by user.

---