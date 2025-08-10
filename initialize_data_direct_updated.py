    def _initialize_data_direct(self):
        """Initialize orphan data directly for small datasets."""
        # Create metadata with validation
        self.orphan_metadata = self.create_orphan_metadata_dict(
            self.comparison_results, 
            self.orphaned_files, 
            self.side, 
            self.source_folder
        )
        
        # Build tree structure
        self.orphan_tree_data = self.build_orphan_tree_structure(self.orphan_metadata)
        
        # Select all items by default
        self.selected_items = set(self.orphaned_files)
        
        # Log details about inaccessible files # v001.0013 added [detailed logging for inaccessible files]
        self.log_inaccessible_files() # v001.0013 added [detailed logging for inaccessible files]
        
        # Update UI
        self.build_orphan_tree()
        self.update_statistics()
        
        # Log initialization results
        accessible_count = sum(1 for m in self.orphan_metadata.values() if m['accessible'])
        self.add_status_message(f"Initialization complete: {accessible_count} accessible files")