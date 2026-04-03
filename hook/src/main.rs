use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;

use serde::Deserialize;

#[derive(Deserialize)]
struct ManagedDb {
    #[serde(default)]
    installed: HashMap<String, InstalledEntry>,
    #[serde(default)]
    aliases: HashMap<String, String>,
}

#[derive(Deserialize)]
struct InstalledEntry {
    location: String,
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        process::exit(1);
    }

    let mut env_tag = args[1].clone();
    let is_macos = cfg!(target_os = "macos");

    let install_dir: PathBuf = if is_macos {
        dirs_home().join("Library/Java/JavaVirtualMachines")
    } else {
        dirs_home().join(".jdk")
    };

    let managed_db_path = install_dir.join(".jdkman");
    let content = match fs::read_to_string(&managed_db_path) {
        Ok(s) => s,
        Err(_) => {
            eprintln!("# jdkman: managed db not found");
            process::exit(1);
        }
    };

    let managed: ManagedDb = match serde_json::from_str(&content) {
        Ok(m) => m,
        Err(_) => {
            eprintln!("# jdkman: failed to parse managed db");
            process::exit(1);
        }
    };

    // Resolve alias → actual slug
    if let Some(resolved) = managed.aliases.get(&env_tag) {
        env_tag = resolved.clone();
    }

    let entry = match managed.installed.get(&env_tag) {
        Some(e) => e,
        None => {
            eprintln!("# jdkman: {env_tag} is not installed");
            process::exit(1);
        }
    };

    let java_home = if is_macos {
        format!("{}/Contents/Home", entry.location)
    } else {
        entry.location.clone()
    };

    let is_fish = env::var("_JDKMAN_SHELL").as_deref() == Ok("fish");

    if is_fish {
        println!("set -gx JAVA_HOME \"{java_home}\"");
        if !is_macos {
            println!("set -gx PATH \"{java_home}/bin\" $_JDKMAN_ORIG_PATH");
        }
    } else {
        println!("export JAVA_HOME=\"{java_home}\"");
        if !is_macos {
            let orig_path = env::var("_JDKMAN_ORIG_PATH").unwrap_or_default();
            println!("export PATH=\"{java_home}/bin:{orig_path}\"");
        }
    }
}

fn dirs_home() -> PathBuf {
    env::var("HOME")
        .map(PathBuf::from)
        .expect("HOME not set")
}
