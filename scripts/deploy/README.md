# Running the GPU, without setting money on fire

AMD Developer Cloud is DigitalOcean underneath, so `doctl` drives it.

**The rule that costs the most if you forget it: a powered-off droplet still bills.** "Stop" is
not free. The only way to stop paying is to snapshot and destroy, then rebuild from the snapshot
when you next need it. Rebuild takes a few minutes; leaving it off overnight costs about $48 of a
$300 allocation.

    up.sh          create from the latest snapshot, or fresh if there is none
    down.sh        snapshot, wait for it, then destroy. The only correct way to pause
    status.sh      what exists right now and what it is costing per hour

## Credits are per account, not pooled

Each account carries its own $100, about 50 GPU-hours, and an instance bills to one account. A
72-hour window for judging is 72 hours on one card — more than any single account holds. So
either hand off between accounts mid-window, or keep the public app serving cached results with
the GPU attached only on demand. The second is less fragile and it is what the app is built for.

Credits also expire 30 days from deposit, and a payment method may be required even while credits
cover the bill. Set a billing alert before the first boot, not after.
