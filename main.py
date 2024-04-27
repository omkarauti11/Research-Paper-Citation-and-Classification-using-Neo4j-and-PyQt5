import os
from dotenv import load_dotenv

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QVBoxLayout
from PyQt5.QtGui import QFont 
from neo4j import GraphDatabase



# Define global variables
direct_citation_path = None
indirect_citation_paths = None


###############################################################################################################


# Database manager class remains unchanged
class DatabaseManager:
    def __init__(self, uri, username, password):
        self._uri = uri
        self._username = username
        self._password = password
        self._driver = None
        self._connection = None

    @property
    def connection(self):
        return self._connection

    def connect(self):
        try:
            self._driver = GraphDatabase.driver(self._uri, auth=(self._username, self._password))
            self._connection = self._driver.session()
            print("Connected to the database successfully.")
        except Exception as e:
            print(f"Error connecting to the database: {str(e)}")

    def disconnect(self):
        if self._driver is not None:
            self._driver.close()
            self._connection = None
    
    def print_direct_citation_result(self, result):
        global direct_citation_path
        record = result
        if record:
            path = record['p']
            nodes = path.nodes
            relationships = path.relationships
            start_node = nodes[0]
            end_node = nodes[-1]
            start_node_id = start_node['id']
            start_node_class = start_node['class']
            end_node_id = end_node['id']
            end_node_class = end_node['class']
            direct_citation_path = f"Paper {start_node_id} ({start_node_class}) --> Paper {end_node_id} ({end_node_class})"
            print("Direct citation found:")
            print(direct_citation_path)
        else:
            direct_citation_path = None
            print("No direct citation found.")

    def print_indirect_citation_result(self, result):
        global indirect_citation_paths
        paths = result
        if paths:
            # Accumulate path strings
            path_strings = []
            visited = set()  # Keep track of visited paper IDs

            for path in paths:
                nodes = path.nodes
                path_string = ""
                for node in nodes:
                    node_id = node['id']
                    node_class = node['class']
                    if node_id not in visited:
                        path_string += f"Paper {node_id} ({node_class}) --> "
                        visited.add(node_id)
                # Remove the last arrow and spaces
                path_string = path_string[:-5]
                path_strings.append(path_string)

            # Concatenate and print all path strings
            indirect_citation_paths = "-->".join(path_strings)
            print(indirect_citation_paths)
        else:
            indirect_citation_paths = None
            print("No indirect citation found.")

    # Indirect citation check
    def check_citation(self, paper_a_id, paper_b_id):
        with self._driver.session() as session:
            result = session.run("""
                MATCH path = (p1:Paper {id: $paper_a_id})-[:CITES*]->(p2:Paper {id: $paper_b_id})
                RETURN path
                LIMIT 1
            """, paper_a_id=paper_a_id, paper_b_id=paper_b_id)
            paths = result.single()
            if paths:
                print(f"Indirect citation found:")
                print(f"Paper {paper_a_id} indirectly cites Paper {paper_b_id}")
                self.print_indirect_citation_result(paths['path'])
                return True
            else:
                return False

    def get_paper_classification(self, paper_id):
        with self._driver.session() as session:
            result = session.run("""
            MATCH (p:Paper {id: $paper_id})
            RETURN p.class as classification
            """, paper_id=paper_id)
            return [record['classification'] for record in result]
        

###############################################################################################################


# Application class with PyQt5 UI elements
class Application(QWidget):
    def __init__(self, db_manager, conn):
        super().__init__()
        self.title = "Research Papers Database Search"
        self.db_manager = db_manager
        self.conn = conn  # Store the database connection
        self.current_search = "citation"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 450, 250)

        self.label_paper_a = QLabel("Paper 1 ID:")
        self.label_paper_a.setFont(QFont("Arial", 13, QFont.Bold))
        self.entry_paper_a = QLineEdit()
        self.entry_paper_a.setFont(QFont("Arial", 12, QFont.Medium))

        self.label_paper_b = QLabel("Paper 2 ID:")
        self.label_paper_b.setFont(QFont("Arial", 13, QFont.Bold))
        self.entry_paper_b = QLineEdit()
        self.entry_paper_b.setFont(QFont("Arial", 12, QFont.Medium))

        self.btn_search = QPushButton("Search Citation")
        self.btn_search.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border: none; padding: 12px 24px; text-align: center; font-size: 16px; }")
        self.btn_search.clicked.connect(self.search)  # Connect the button to the search method

        self.toggle_search_btn = QPushButton("Switch to Classification Search")
        self.toggle_search_btn.setStyleSheet("QPushButton { background-color: #008CBA; color: white; border: none; padding: 12px 24px; text-align: center; font-size: 16px; }")
        self.toggle_search_btn.clicked.connect(self.toggle_search)  # Connect the button to the toggle_search method

        layout = QVBoxLayout()
        layout.addWidget(self.label_paper_a)
        layout.addWidget(self.entry_paper_a)
        layout.addWidget(self.label_paper_b)
        layout.addWidget(self.entry_paper_b)
        layout.addWidget(self.btn_search)
        layout.addWidget(self.toggle_search_btn)

        self.setLayout(layout)
        self.show()


    def toggle_search(self):
        if self.current_search == "citation":
            self.current_search = "classification"
            self.btn_search.setText("Search classification")
            self.toggle_search_btn.setText("Switch to Citation Search")
            self.label_paper_b.hide()
            self.entry_paper_b.hide()
        else:
            self.current_search = "citation"
            self.btn_search.setText("Search Citation")
            self.toggle_search_btn.setText("Switch to Classification Search")
            self.label_paper_b.show()
            self.entry_paper_b.show()

    # # Direct citation check
    #     query_direct = f'''MATCH p=(:Paper{{id:"{paper_a_id}"}})-[r:CITES]->(:Paper{{id:"{paper_b_id}"}}) RETURN p'''

    def search(self):
        if self.current_search == "citation":
            paper_a_id = self.entry_paper_a.text()
            paper_b_id = self.entry_paper_b.text()
            
            # Direct citation check
            query_direct = f'''MATCH p=(:Paper{{id:"{paper_a_id}"}})-[r:CITES]->(:Paper{{id:"{paper_b_id}"}}) RETURN p'''

            with self.db_manager._driver.session() as session:
                result_direct = session.run(query_direct).single()
                self.db_manager.print_direct_citation_result(result_direct)

                if result_direct:
                    # Direct citation found
                    global direct_citation_path
                    QMessageBox.information(self, "Citation Search Result", f"Paper {paper_a_id} directly cites Paper {paper_b_id}\n\n{direct_citation_path}")
                else:
                    # No direct citation found
                    # Indirect citation check
                    cited = self.db_manager.check_citation(paper_a_id, paper_b_id)
                    if cited:
                        # Indirect citation found
                        global indirect_citation_paths
                        QMessageBox.information(self, "Citation Search Result", f"Paper {paper_a_id} indirectly cites Paper {paper_b_id} but not directly\n\n{indirect_citation_paths}")
                    else:
                        # No citation found
                        print("No citation found.")
                        QMessageBox.information(self, "Citation Search Result", f"Paper {paper_a_id} does not cite Paper {paper_b_id}")
        else:
            paper_id = self.entry_paper_a.text()
            classifications = self.db_manager.get_paper_classification(paper_id)
            QMessageBox.information(self, "Classification Search Result", f"Paper {paper_id} has the following classifications: {', '.join(classifications)}")


#################################################################################################################


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Neo4j connection details
    username = os.getenv("DB_USERNAME")
    # username = "neo4j"

    password = os.getenv("DB_PASSWORD")
    # password = "admin123"

    port = os.getenv("PORT")

    # uri = "bolt://localhost:7687"   ## for neo4j console
    uri = f"bolt://localhost:{port}"
    # uri = "bolt://localhost:7689"  ## for neo4j desktop

    # print(f"{username}, {password}, {port}, {uri}")
    
    # Create and connect to database manager
    db_manager = DatabaseManager(uri, username, password)
    db_manager.connect()

    # Create Neo4j connection (conn) if needed
    conn = db_manager.connection

    # Create and run the application
    app = QApplication(sys.argv)
    ex = Application(db_manager, conn)
    sys.exit(app.exec_())

    # Disconnect from the database
    db_manager.disconnect()


