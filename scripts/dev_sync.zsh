#!/bin/zsh
uv sync "$@"
cargo build --release --manifest-path hook/Cargo.toml
cp hook/target/release/jdk-hook-env .venv/bin/
