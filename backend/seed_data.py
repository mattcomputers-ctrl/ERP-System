"""Seed script to populate initial data for BatchFlow ERP."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models import *


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already seeded. Skipping.")
            return

        # --- Admin User ---
        admin = User(
            username="admin",
            email="admin@batchflow.local",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)

        # --- User Groups ---
        groups_data = [
            ("Administrators", "Full system access"),
            ("Production Managers", "Manufacturing and QC access"),
            ("Warehouse Staff", "Inventory management access"),
            ("Sales Team", "Sales order management"),
            ("Purchasing Team", "Purchase order management"),
            ("QC Inspectors", "Quality control testing"),
        ]
        groups = {}
        for name, desc in groups_data:
            g = UserGroup(name=name, description=desc)
            db.add(g)
            groups[name] = g
        db.flush()

        # --- Permissions for groups ---
        modules = ["inventory", "sales", "purchasing", "manufacturing", "quality", "reporting", "admin"]
        actions = ["create", "read", "update", "delete", "approve", "export"]

        # Admins get everything
        for mod in modules:
            for act in actions:
                db.add(GroupPermission(group_id=groups["Administrators"].id, module=mod, action=act))

        # Production Managers
        for mod in ["manufacturing", "quality", "inventory", "reporting"]:
            for act in ["create", "read", "update", "approve"]:
                db.add(GroupPermission(group_id=groups["Production Managers"].id, module=mod, action=act))

        # Warehouse Staff
        for act in ["create", "read", "update"]:
            db.add(GroupPermission(group_id=groups["Warehouse Staff"].id, module="inventory", action=act))
        db.add(GroupPermission(group_id=groups["Warehouse Staff"].id, module="reporting", action="read"))

        # Sales Team
        for act in ["create", "read", "update"]:
            db.add(GroupPermission(group_id=groups["Sales Team"].id, module="sales", action=act))
        db.add(GroupPermission(group_id=groups["Sales Team"].id, module="inventory", action="read"))
        db.add(GroupPermission(group_id=groups["Sales Team"].id, module="reporting", action="read"))

        # Purchasing Team
        for act in ["create", "read", "update"]:
            db.add(GroupPermission(group_id=groups["Purchasing Team"].id, module="purchasing", action=act))
        db.add(GroupPermission(group_id=groups["Purchasing Team"].id, module="inventory", action="read"))
        db.add(GroupPermission(group_id=groups["Purchasing Team"].id, module="reporting", action="read"))

        # QC Inspectors
        for act in ["create", "read", "update", "approve"]:
            db.add(GroupPermission(group_id=groups["QC Inspectors"].id, module="quality", action=act))
        db.add(GroupPermission(group_id=groups["QC Inspectors"].id, module="inventory", action="read"))

        # --- Sample Users ---
        sample_users = [
            ("jsmith", "jsmith@batchflow.local", "John Smith", "Production Managers"),
            ("mwilson", "mwilson@batchflow.local", "Mary Wilson", "Sales Team"),
            ("bjones", "bjones@batchflow.local", "Bob Jones", "Warehouse Staff"),
            ("slee", "slee@batchflow.local", "Sarah Lee", "Purchasing Team"),
            ("dtaylor", "dtaylor@batchflow.local", "David Taylor", "QC Inspectors"),
        ]
        for uname, email, fname, gname in sample_users:
            u = User(username=uname, email=email, hashed_password=hash_password("password123"), full_name=fname)
            db.add(u)
            db.flush()
            db.add(UserGroupAssociation(user_id=u.id, group_id=groups[gname].id))

        # --- GL Groups ---
        gl_groups_data = [
            ("Raw Materials", "Raw material inventory"),
            ("Packaging", "Packaging materials"),
            ("Finished Goods", "Finished products"),
            ("Work in Process", "Items in production"),
            ("Consumables", "Consumable supplies"),
        ]
        gl_groups = {}
        for name, desc in gl_groups_data:
            g = GLGroup(name=name, description=desc)
            db.add(g)
            gl_groups[name] = g
        db.flush()

        # GL Account Mappings
        mappings = {
            "Raw Materials": [
                ("sales", "Raw Material Sales", "4100"),
                ("cogs", "Raw Material COGS", "5100"),
                ("inventory_asset", "Raw Material Inventory", "1300"),
                ("inventory_adjustment", "RM Inventory Adjustment", "5150"),
            ],
            "Finished Goods": [
                ("sales", "Product Sales", "4000"),
                ("cogs", "Product COGS", "5000"),
                ("inventory_asset", "Finished Goods Inventory", "1310"),
                ("inventory_adjustment", "FG Inventory Adjustment", "5050"),
            ],
            "Packaging": [
                ("sales", "Packaging Sales", "4200"),
                ("cogs", "Packaging COGS", "5200"),
                ("inventory_asset", "Packaging Inventory", "1320"),
                ("inventory_adjustment", "Pkg Inventory Adjustment", "5250"),
            ],
        }
        for gl_name, accts in mappings.items():
            for atype, aname, anum in accts:
                db.add(GLAccountMapping(
                    gl_group_id=gl_groups[gl_name].id,
                    account_type=atype, account_name=aname, account_number=anum,
                ))

        # --- Units of Measure ---
        uoms_data = [
            ("Kilogram", "kg", "weight"),
            ("Gram", "g", "weight"),
            ("Pound", "lb", "weight"),
            ("Ounce", "oz", "weight"),
            ("Liter", "L", "volume"),
            ("Milliliter", "mL", "volume"),
            ("Gallon", "gal", "volume"),
            ("Each", "ea", "count"),
            ("Case", "cs", "count"),
            ("Pallet", "plt", "count"),
        ]
        uoms = {}
        for name, abbr, cat in uoms_data:
            u = UnitOfMeasure(name=name, abbreviation=abbr, category=cat)
            db.add(u)
            uoms[abbr] = u
        db.flush()

        # --- Warehouses ---
        wh_main = Warehouse(code="MAIN", name="Main Warehouse", address="100 Industrial Blvd")
        wh_raw = Warehouse(code="RAW", name="Raw Materials Warehouse", address="100 Industrial Blvd, Bldg B")
        db.add_all([wh_main, wh_raw])
        db.flush()

        locs = [
            Location(warehouse_id=wh_main.id, code="A-01", name="Aisle A, Rack 1"),
            Location(warehouse_id=wh_main.id, code="A-02", name="Aisle A, Rack 2"),
            Location(warehouse_id=wh_main.id, code="B-01", name="Aisle B, Rack 1"),
            Location(warehouse_id=wh_raw.id, code="R-01", name="Raw Storage 1"),
            Location(warehouse_id=wh_raw.id, code="R-02", name="Raw Storage 2"),
        ]
        db.add_all(locs)
        db.flush()

        # --- Items ---
        items_data = [
            ("RM-001", "Titanium Dioxide", "raw_material", "Raw Materials", "kg"),
            ("RM-002", "Calcium Carbonate", "raw_material", "Raw Materials", "kg"),
            ("RM-003", "Acrylic Resin", "raw_material", "Raw Materials", "kg"),
            ("RM-004", "Solvent Blend", "raw_material", "Raw Materials", "L"),
            ("RM-005", "Yellow Oxide Pigment", "raw_material", "Raw Materials", "kg"),
            ("PKG-001", "5 Gallon Pail", "packaging", "Packaging", "ea"),
            ("PKG-002", "1 Gallon Can", "packaging", "Packaging", "ea"),
            ("PKG-003", "Pail Label", "packaging", "Packaging", "ea"),
            ("FG-001", "Premium White Coating", "finished_good", "Finished Goods", "kg"),
            ("FG-002", "Standard White Paint", "finished_good", "Finished Goods", "gal"),
            ("FG-003", "Yellow Industrial Coating", "finished_good", "Finished Goods", "kg"),
        ]
        items = {}
        for code, name, itype, gl_name, uom_abbr in items_data:
            item = Item(
                item_code=code, name=name, item_type=itype,
                gl_group_id=gl_groups[gl_name].id,
                primary_uom_id=uoms[uom_abbr].id,
                is_lot_tracked=True,
                reorder_level=100 if itype == "raw_material" else 50,
                safety_stock=50 if itype == "raw_material" else 25,
            )
            db.add(item)
            items[code] = item
        db.flush()

        # --- Vendors ---
        vendors = [
            Vendor(code="V-001", name="ChemSupply Inc", contact_name="Tom Brown", email="tom@chemsupply.com", phone="555-0101", payment_terms="Net 30"),
            Vendor(code="V-002", name="PigmentCo", contact_name="Lisa White", email="lisa@pigmentco.com", phone="555-0102", payment_terms="Net 45"),
            Vendor(code="V-003", name="PackagePro", contact_name="Mike Green", email="mike@packagepro.com", phone="555-0103", payment_terms="Net 30"),
        ]
        db.add_all(vendors)

        # --- Customers ---
        customers = [
            Customer(code="C-001", name="ABC Contractors", contact_name="Jim Davis", email="jim@abccontractors.com", phone="555-0201", payment_terms="Net 30"),
            Customer(code="C-002", name="BuildRight Supply", contact_name="Karen Miller", email="karen@buildright.com", phone="555-0202", payment_terms="Net 45"),
            Customer(code="C-003", name="Industrial Coatings Co", contact_name="Steve Clark", email="steve@indcoatings.com", phone="555-0203", payment_terms="Net 30"),
        ]
        db.add_all(customers)

        # --- Formulas ---
        formula = Formula(
            code="F-001", name="Premium White Coating Formula",
            product_item_id=items["FG-001"].id,
            description="Premium quality white coating for industrial use",
        )
        version = FormulaVersion(
            version_number=1, batch_size=100,
            batch_uom_id=uoms["kg"].id,
            expected_yield_percent=98,
            is_current=True,
            notes="Standard batch - 100kg",
        )
        version.ingredients = [
            FormulaIngredient(item_id=items["RM-001"].id, sequence=1, quantity=30, uom_id=uoms["kg"].id, percentage=30),
            FormulaIngredient(item_id=items["RM-002"].id, sequence=2, quantity=20, uom_id=uoms["kg"].id, percentage=20),
            FormulaIngredient(item_id=items["RM-003"].id, sequence=3, quantity=35, uom_id=uoms["kg"].id, percentage=35),
            FormulaIngredient(item_id=items["RM-004"].id, sequence=4, quantity=15, uom_id=uoms["L"].id, percentage=15),
        ]
        formula.versions.append(version)
        db.add(formula)

        formula2 = Formula(
            code="F-002", name="Yellow Industrial Coating Formula",
            product_item_id=items["FG-003"].id,
        )
        v2 = FormulaVersion(
            version_number=1, batch_size=100,
            batch_uom_id=uoms["kg"].id,
            expected_yield_percent=97,
            is_current=True,
        )
        v2.ingredients = [
            FormulaIngredient(item_id=items["RM-005"].id, sequence=1, quantity=25, uom_id=uoms["kg"].id, percentage=25),
            FormulaIngredient(item_id=items["RM-002"].id, sequence=2, quantity=25, uom_id=uoms["kg"].id, percentage=25),
            FormulaIngredient(item_id=items["RM-003"].id, sequence=3, quantity=35, uom_id=uoms["kg"].id, percentage=35),
            FormulaIngredient(item_id=items["RM-004"].id, sequence=4, quantity=15, uom_id=uoms["L"].id, percentage=15),
        ]
        formula2.versions.append(v2)
        db.add(formula2)

        # --- QC Specifications ---
        spec_tio2 = QCSpecification(
            name="TiO2 Incoming Inspection",
            item_id=items["RM-001"].id,
            spec_type="incoming",
        )
        spec_tio2.tests = [
            QCTest(test_name="Purity", test_method="XRF Analysis", target_value=99.5, min_value=99.0, max_value=100.0, uom="%", sequence=1),
            QCTest(test_name="Particle Size D50", test_method="Laser Diffraction", target_value=0.25, min_value=0.20, max_value=0.30, uom="micron", sequence=2),
            QCTest(test_name="Moisture Content", test_method="LOD at 105C", target_value=0.3, min_value=0.0, max_value=0.5, uom="%", sequence=3),
        ]
        db.add(spec_tio2)

        spec_fg = QCSpecification(
            name="White Coating FG Inspection",
            item_id=items["FG-001"].id,
            spec_type="finished_goods",
        )
        spec_fg.tests = [
            QCTest(test_name="Viscosity", test_method="Brookfield RVT", target_value=85, min_value=80, max_value=95, uom="KU", sequence=1),
            QCTest(test_name="Density", test_method="Weight per Gallon Cup", target_value=11.2, min_value=11.0, max_value=11.5, uom="lb/gal", sequence=2),
            QCTest(test_name="pH", test_method="pH Meter", target_value=8.5, min_value=8.0, max_value=9.0, uom="pH", sequence=3),
            QCTest(test_name="Gloss 60°", test_method="Gloss Meter", target_value=80, min_value=75, max_value=90, uom="GU", sequence=4),
        ]
        db.add(spec_fg)

        db.commit()
        print("Database seeded successfully!")
        print("\nDefault admin account:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nSample users (password: password123):")
        print("  jsmith  - Production Manager")
        print("  mwilson - Sales Team")
        print("  bjones  - Warehouse Staff")
        print("  slee    - Purchasing Team")
        print("  dtaylor - QC Inspector")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
