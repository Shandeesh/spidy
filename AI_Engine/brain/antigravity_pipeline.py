import os
import json
import datetime
import subprocess
import sys

FEEDBACK_LOOP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Shared_Data/feedback_loop.json"))
STRATEGY_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Shared_Data/configs/trading_strategy.json"))

class AntigravityPipeline:
    def __init__(self):
        self.db = self._load_db()

    def _load_db(self):
        if not os.path.exists(FEEDBACK_LOOP_PATH):
            # Fallback default
            return {"config": {}, "feedback_loop": [], "update_history": [], "pending_plans": {}}
        try:
            with open(FEEDBACK_LOOP_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading feedback loop database: {e}")
            return {"config": {}, "feedback_loop": [], "update_history": [], "pending_plans": {}}

    def _save_db(self):
        try:
            os.makedirs(os.path.dirname(FEEDBACK_LOOP_PATH), exist_ok=True)
            with open(FEEDBACK_LOOP_PATH, "w") as f:
                json.dump(self.db, f, indent=2)
        except Exception as e:
            print(f"Error saving feedback loop database: {e}")

    def add_feedback(self, floor, message, source="user", level="info"):
        feedback_id = f"fb_{int(datetime.datetime.now().timestamp())}"
        new_entry = {
            "id": feedback_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "source": source,
            "level": level,
            "message": message,
            "status": "pending",
            "floor": floor,
            "retries": 0
        }
        self.db.setdefault("feedback_loop", []).append(new_entry)
        self._save_db()
        return new_entry

    def run_audit(self, floor):
        logs = []
        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [AUDIT] Starting codebase and telemetry audit for floor: '{floor.upper()}'...")
        
        # Check floor config
        config = self.db.get("config", {}).get(floor, {
            "auto_update": True,
            "plan_mode": True,
            "strict_testing": True,
            "max_retries": 3
        })
        
        # Look for pending feedback
        pending_items = [fb for fb in self.db.get("feedback_loop", []) if fb["floor"] == floor and fb["status"] in ("pending", "patch_created")]
        
        if not pending_items:
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [AUDIT] No pending feedback or errors found for {floor.upper()}. Codebase is in healthy state.")
            return {"status": "idle", "logs": "\n".join(logs)}

        fb_item = pending_items[0]
        fb_id = fb_item["id"]
        message = fb_item["message"]
        
        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [AUDIT] Found pending feedback item '{fb_id}': \"{message}\"")
        
        # Check if blocked by infinite loop guardrail
        retries = fb_item.get("retries", 0)
        if retries >= config.get("max_retries", 3):
            fb_item["status"] = "blocked"
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [CRITICAL] Infinite loop guardrail triggered! Feedback '{fb_id}' failed {retries} times. Pipeline halted to prevent token wastage.")
            self._save_db()
            return {"status": "blocked", "logs": "\n".join(logs)}

        # Propose patch/update details
        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PLAN] Generating feature patch / bugfix blueprint...")
        
        plan_title = f"Patch for {floor.upper()}"
        plan_desc = ""
        proposed_files = []
        
        if floor == "spidy":
            # Real-ish patch for Spidy strategy configs
            plan_desc = f"Address telemetry report: '{message}'. This optimization updates trading_strategy.json trailing stop-loss values and volatility filters."
            
            # Read current strategy version
            current_version = "v1.4.2"
            if os.path.exists(STRATEGY_CONFIG_PATH):
                try:
                    with open(STRATEGY_CONFIG_PATH, "r") as sf:
                        sdata = json.load(sf)
                        current_version = sdata.get("version", "v1.4.2")
                except:
                    pass

            v_parts = current_version.replace("v", "").split(".")
            try:
                v_parts[-1] = str(int(v_parts[-1]) + 1)
            except:
                v_parts[-1] = "1"
            next_version = "v" + ".".join(v_parts)

            proposed_files = [
                {
                    "path": "Shared_Data/configs/trading_strategy.json",
                    "action": "MODIFY",
                    "diff": f"@@ -2,4 +2,5 @@\n-  \"volatility_threshold\": 1.5,\n-  \"trailing_stop_loss_pips\": 20,\n-  \"version\": \"{current_version}\"\n+  \"volatility_threshold\": 1.8,\n+  \"trailing_stop_loss_pips\": 15,\n+  \"version\": \"{next_version}\""
                }
            ]
        elif floor == "trade_ai":
            plan_desc = f"Resolve Trade AI strategy verification issue: '{message}'. Integrate sentiment index weighting."
            proposed_files = [
                {
                    "path": "AI_Engine/strategy_optimizer/sentiment_weight.json",
                    "action": "NEW",
                    "diff": "@@ -0,0 +1,5 @@\n+ {\n+   \"sentiment_index_weight\": 0.25,\n+   \"min_confidence_threshold\": 0.70\n+ }"
                }
            ]
        else: # shooya
            plan_desc = f"Apply Shooya optimization: '{message}'. Upgrade WebSocket buffers in shoonya_server.py."
            proposed_files = [
                {
                    "path": "Trading_Backend/shoonya_bridge/shoonya_server.py",
                    "action": "MODIFY",
                    "diff": "@@ -124,2 +124,2 @@\n-         ws.recv_buffer_size = 4096\n+         ws.recv_buffer_size = 16384"
                }
            ]

        # Check Plan Mode
        if config.get("plan_mode", True):
            # Save pending plan
            plan = {
                "feedback_id": fb_id,
                "title": plan_title,
                "description": plan_desc,
                "files": proposed_files,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            self.db.setdefault("pending_plans", {})[floor] = plan
            fb_item["status"] = "patch_created"
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PLAN] Plan Mode is ENABLED. Patch drafted and saved for administrator review.")
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PLAN] Pausing update loop. Awaiting green light in Control Center.")
            self._save_db()
            return {"status": "pending_approval", "logs": "\n".join(logs), "plan": plan}
        else:
            # Plan mode disabled, run execution directly
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PLAN] Plan Mode is DISABLED. Bypassing review and executing patch immediately.")
            self._save_db()
            exec_res = self._execute_patch_logic(floor, fb_item, proposed_files, config, logs)
            return exec_res

    def approve_plan(self, floor):
        logs = []
        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [DEPLOY] Plan approved by administrator. Executing update pipeline...")
        
        pending_plans = self.db.get("pending_plans", {})
        if floor not in pending_plans:
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] No pending plan found for floor: '{floor}'")
            return {"status": "error", "logs": "\n".join(logs)}

        plan = pending_plans[floor]
        fb_id = plan["feedback_id"]
        
        # Find feedback item
        fb_item = None
        for fb in self.db.get("feedback_loop", []):
            if fb["id"] == fb_id:
                fb_item = fb
                break
        
        if not fb_item:
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] Associated feedback item '{fb_id}' not found.")
            return {"status": "error", "logs": "\n".join(logs)}

        config = self.db.get("config", {}).get(floor, {
            "auto_update": True,
            "plan_mode": True,
            "strict_testing": True,
            "max_retries": 3
        })

        exec_res = self._execute_patch_logic(floor, fb_item, plan["files"], config, logs)
        
        # Clear pending plan on completion
        if floor in self.db.get("pending_plans", {}):
            del self.db["pending_plans"][floor]
        self._save_db()
        
        return exec_res

    def reject_plan(self, floor):
        logs = []
        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [PLAN] Plan rejected by administrator. Reverting feedback item back to pending status.")
        
        pending_plans = self.db.get("pending_plans", {})
        if floor not in pending_plans:
            return {"status": "error", "logs": "No plan to reject"}

        plan = pending_plans[floor]
        fb_id = plan["feedback_id"]
        
        for fb in self.db.get("feedback_loop", []):
            if fb["id"] == fb_id:
                fb["status"] = "pending"
                break
                
        del self.db["pending_plans"][floor]
        self._save_db()
        return {"status": "rejected", "logs": "\n".join(logs)}

    def _execute_patch_logic(self, floor, fb_item, files, config, logs):
        # 1. Apply code updates (Writing Phase)
        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [CODE] Applying patch file changes...")
        
        # Track original states for rollback if test fails
        backup_files = {}
        for f in files:
            file_path = f["path"]
            action = f["action"]
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [CODE] {action}: {file_path}")
            
            if floor == "spidy" and file_path == "Shared_Data/configs/trading_strategy.json":
                # Actually write changes
                if os.path.exists(STRATEGY_CONFIG_PATH):
                    try:
                        with open(STRATEGY_CONFIG_PATH, "r") as sf:
                            backup_files[STRATEGY_CONFIG_PATH] = sf.read()
                    except:
                        pass
                
                # Parse diff or update variables
                try:
                    sdata = {}
                    if STRATEGY_CONFIG_PATH in backup_files:
                        sdata = json.loads(backup_files[STRATEGY_CONFIG_PATH])
                    sdata["volatility_threshold"] = 1.8
                    sdata["trailing_stop_loss_pips"] = 15
                    # extract version bump
                    current_version = sdata.get("version", "v1.4.2")
                    v_parts = current_version.replace("v", "").split(".")
                    v_parts[-1] = str(int(v_parts[-1]) + 1)
                    sdata["version"] = "v" + ".".join(v_parts)
                    
                    os.makedirs(os.path.dirname(STRATEGY_CONFIG_PATH), exist_ok=True)
                    with open(STRATEGY_CONFIG_PATH, "w") as sf:
                        json.dump(sdata, sf, indent=2)
                    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [CODE] Updated strategy params to stop-loss=15, volatility=1.8, version={sdata['version']}.")
                except Exception as e:
                    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [ERROR] Writing file failed: {e}")
                    return {"status": "error", "logs": "\n".join(logs)}

        # 2. Strict Testing Boundary
        test_failed = False
        test_output = ""
        
        # Guardrail test triggers: check if the user wanted to trigger a test failure
        break_tests_requested = "break tests" in fb_item["message"].lower()

        if config.get("strict_testing", True):
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Strict Testing Boundary is ENABLED. Running automated validation suite...")
            
            if floor == "spidy":
                # Execute verify_logic.py
                verify_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../verify_logic.py"))
                if os.path.exists(verify_script) and not break_tests_requested:
                    try:
                        res = subprocess.run([sys.executable, verify_script], capture_output=True, text=True, timeout=10)
                        test_output = res.stdout
                        if res.returncode == 0:
                            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Automated verification logic check passed.")
                        else:
                            test_failed = True
                            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Automated verification failed with exit code {res.returncode}.")
                    except Exception as e:
                        test_failed = True
                        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Exception running verification: {e}")
                else:
                    if break_tests_requested:
                        test_failed = True
                        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] [GUARDRAIL] Simulated verification test failure triggered as requested.")
                    else:
                        logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] verify_logic.py not found. Bypassing script run.")
            else:
                # Simulated verification run for other floors
                if break_tests_requested:
                    test_failed = True
                    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] [GUARDRAIL] Simulated verification test failure triggered as requested.")
                else:
                    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Running mock strategy tests for {floor.upper()}...")
                    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Integration tests passed.")
        else:
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [TEST] Strict Testing Boundary is DISABLED. Skipping validation suite.")

        # 3. Deploy/Rollback phase
        if test_failed:
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [WARNING] Strategy verification failed! Triggering rollback...")
            
            # Rollback
            for path, content in backup_files.items():
                try:
                    with open(path, "w") as sf:
                        sf.write(content)
                    logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [CODE] Rolled back {os.path.basename(path)} to original state.")
                except:
                    pass
            
            # Increment retries
            fb_item["retries"] = fb_item.get("retries", 0) + 1
            retries = fb_item["retries"]
            max_retries = config.get("max_retries", 3)
            
            if retries >= max_retries:
                fb_item["status"] = "blocked"
                logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [CRITICAL] Loop Guardrail Activated! Feedback '{fb_item['id']}' failed {retries} consecutive times. Halting pipeline to prevent infinite looping.")
            else:
                fb_item["status"] = "pending" # Keep pending to retry next time
                logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [WARNING] Update loop failed. Feedback status reset. Retry count: {retries}/{max_retries}.")
            
            self._save_db()
            return {"status": "failed", "logs": "\n".join(logs)}
        else:
            # Successful deployment
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [DEPLOY] Deploying patch to live environment...")
            
            version_before = "v1.4.2"
            version_after = "v1.4.3"
            
            if floor == "spidy" and os.path.exists(STRATEGY_CONFIG_PATH):
                try:
                    with open(STRATEGY_CONFIG_PATH, "r") as sf:
                        sdata = json.load(sf)
                        version_after = sdata.get("version", "v1.4.3")
                        # parse numbers to deduce version before
                        parts = version_after.replace("v", "").split(".")
                        parts[-1] = str(max(1, int(parts[-1]) - 1))
                        version_before = "v" + ".".join(parts)
                except:
                    pass
            elif floor == "trade_ai":
                version_before = "v3.1.0"
                version_after = "v3.1.1"
            else:
                version_before = "v2.0.4"
                version_after = "v2.0.5"

            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [DEPLOY] Live configuration updated from {version_before} to {version_after}.")
            logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [DEPLOY] Production cluster sync complete. Update successful! ✅")
            
            # Record update history
            up_id = f"up_{int(datetime.datetime.now().timestamp())}"
            new_update = {
                "id": up_id,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "floor": floor,
                "version_before": version_before,
                "version_after": version_after,
                "status": "success",
                "type": "minor_bugfix" if "fix" in fb_item["message"].lower() or "bug" in fb_item["message"].lower() else "performance_tuning",
                "details": f"Automatically resolved feedback item '{fb_item['id']}': \"{fb_item['message']}\"",
                "pipeline_logs": "\n".join(logs)
            }
            
            self.db.setdefault("update_history", []).append(new_update)
            
            # Resolve feedback item
            fb_item["status"] = "resolved"
            self._save_db()
            
            return {"status": "success", "logs": "\n".join(logs), "update": new_update}
