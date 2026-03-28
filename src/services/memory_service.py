import json
from models.memory import MemoryFact, CategoryRegistry

TABLE_NAME = "user_memory"


class MemoryService:
    def __init__(self, table):
        self.table = table

    def get_categories(self, user_id):
        resp = self.table.get_item(Key={"user_id": user_id, "category": CategoryRegistry.METADATA_SK})
        item = resp.get("Item")
        if not item:
            return CategoryRegistry(user_id=user_id)
        return CategoryRegistry.from_dynamo(item)

    def save_categories(self, registry):
        self.table.put_item(Item=registry.to_dynamo())

    def get_fact(self, user_id, category):
        resp = self.table.get_item(Key={"user_id": user_id, "category": category})
        item = resp.get("Item")
        if not item:
            return None
        return MemoryFact.from_dynamo(item)

    def get_all_facts(self, user_id):
        resp = self.table.query(
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id},
        )
        return [
            MemoryFact.from_dynamo(i)
            for i in resp.get("Items", [])
            if i["category"] != CategoryRegistry.METADATA_SK
        ]

    def save_fact(self, fact):
        self.table.put_item(Item=fact.to_dynamo())

    def delete_fact(self, user_id, category):
        self.table.delete_item(Key={"user_id": user_id, "category": category})
