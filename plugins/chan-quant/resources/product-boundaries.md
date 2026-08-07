# Product boundaries

Chan Quant is an **Experimental / Research Preview** and the plugin is a read-only local research adapter. The Python backend owns indicators, structural state, signals, event studies, portfolio-study assumptions, and data-quality conclusions. Skills format and route results; they do not recalculate them.

The plugin does not connect to brokers, place orders, read credentials, manage accounts, publish signals, promise performance, or provide individualized buy/sell/hold/position advice. `CANDIDATE_BUY` and `CANDIDATE_EXIT` remain draft research labels.

The plugin connects only to configured HTTP loopback addresses. It never starts or stops Chan Quant, never writes market data or user state, and never uses Git at runtime. Remote access is owned by the backend and can be disabled with `CHAN_QUANT_REMOTE_NETWORK_ENABLED`.

