import asyncio

from app.database import engine, Base
import app.models


def remove_duplicate_indexes():
    """
    Remove duplicate SQLAlchemy Index objects with the same name.
    This handles cases where index=True and an explicit Index(...)
    create the same index.
    """
    removed = []

    for table in Base.metadata.tables.values():
        seen = {}

        for index in list(table.indexes):
            if index.name in seen:
                table.indexes.discard(index)
                removed.append(
                    f"{table.name}.{index.name}"
                )
            else:
                seen[index.name] = index

    if removed:
        print("\nRemoved duplicate indexes:")
        for item in removed:
            print(f"  - {item}")
    else:
        print("\nNo duplicate indexes found.")


async def main():
    print("\n========================================")
    print("CivicLens Database Setup")
    print("========================================")

    print("\n1. Loading models...")
    print(f"Tables found: {len(Base.metadata.tables)}")

    print("\n2. Cleaning duplicate indexes...")
    remove_duplicate_indexes()

    print("\n3. Creating database tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()

    print("\n========================================")
    print("SUCCESS!")
    print("Database tables created successfully!")
    print("========================================")


if __name__ == "__main__":
    asyncio.run(main())
