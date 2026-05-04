import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from constant import FEATURE_COLS, GESTURE_MAP

def create_interactive_viewer(data_path):
    data = np.load(data_path, allow_pickle=True)
    X, y = data['features'], data['labels']
    unique_labels = sorted(np.unique(y))
    colors = ['gray', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    class State:
        def __init__(self): self.idx = 0
    state = State()

    fig, (ax_acc, ax_gyro) = plt.subplots(2, 1, figsize=(12, 8))
    plt.subplots_adjust(bottom=0.2)

    def update(label_idx):
        ax_acc.clear()
        ax_gyro.clear()
        
        label = unique_labels[label_idx]
        raw_subset = X[y == label]
        
        # --- FIX: Align variable-length samples to 100 steps ---
        target_len = 100 
        aligned_samples = []
        for s in raw_subset:
            if len(s) >= target_len:
                aligned_samples.append(s[:target_len])
            else:
                # Pad with zeros if recording was too short
                padding = np.zeros((target_len - len(s), s.shape[1]))
                aligned_samples.append(np.vstack((s, padding)))
        
        subset = np.array(aligned_samples)
        mean_sig = np.mean(subset, axis=0)
        std_sig = np.std(subset, axis=0)
        t = np.arange(target_len)

        # Plot Accelerometer (Indices 1, 2, 3)
        for f in range(0, 3):
            ax_acc.plot(t, mean_sig[:, f], label=FEATURE_COLS[f], color=colors[f])
            ax_acc.fill_between(t, mean_sig[:, f]-std_sig[:, f], 
                                mean_sig[:, f]+std_sig[:, f], color=colors[f], alpha=0.1)
        
        # Plot Gyroscope (Indices 4, 5, 6)
        for f in range(3, 6):
            ax_gyro.plot(t, mean_sig[:, f], label=FEATURE_COLS[f], color=colors[f])
            ax_gyro.fill_between(t, mean_sig[:, f]-std_sig[:, f], 
                                 mean_sig[:, f]+std_sig[:, f], color=colors[f], alpha=0.1)

        label_name = GESTURE_MAP.get(unique_labels[label_idx], f"Unknown ({unique_labels[label_idx]})")
        ax_acc.set_title(f"Gesture: {label_name}")
        ax_gyro.set_title(f"Angular Velocity")
        ax_acc.legend(loc='upper right', fontsize='x-small')
        ax_gyro.legend(loc='upper right', fontsize='x-small')
        fig.canvas.draw_idle()

    # UI Controls
    ax_prev, ax_next = plt.axes([0.7, 0.05, 0.1, 0.075]), plt.axes([0.81, 0.05, 0.1, 0.075])
    btn_prev, btn_next = Button(ax_prev, 'Previous'), Button(ax_next, 'Next')
    btn_next.on_clicked(lambda e: (setattr(state, 'idx', (state.idx + 1) % len(unique_labels)), update(state.idx)))
    btn_prev.on_clicked(lambda e: (setattr(state, 'idx', (state.idx - 1) % len(unique_labels)), update(state.idx)))

    update(0)
    plt.show()

if __name__ == "__main__":
    DATA_DIR = 'dataset/gesture_data_consolidated.npz'
    create_interactive_viewer(DATA_DIR)