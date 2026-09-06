import random
from locust import HttpUser, task, between

class StudentPortalUser(HttpUser):
    """
    Simulates real student portal users asking questions from course notes and syllabus.
    Reference: Phase 13 of technical plan.
    """
    wait_time = between(1, 3)

    @task(5)
    def ask_avl_tree(self):
        self.client.post("/api/v1/ask", json={
            "question": "What is an AVL tree and what is its rebalancing rule?",
            "department": "ComputerScience",
            "course": "CS401"
        })

    @task(3)
    def ask_office_hours(self):
        self.client.post("/api/v1/ask", json={
            "question": "When are the instructor office hours for CS401?",
            "department": "ComputerScience",
            "course": "CS401"
        })

    @task(2)
    def ask_plan(self):
        self.client.post("/api/v1/ask", json={
            "question": "What are the five design principles behind every phase of the university RAG plan?",
            "department": "ComputerScience"
        })

    @task(1)
    def check_health(self):
        self.client.get("/health")
