import type {
  BoardStorageIssue,
  BuiltInBoard,
  StoredBoardV1,
} from "../comparisonBoards";


interface ComparisonBoardPickerProps {
  builtInBoards: BuiltInBoard[];
  customBoards: StoredBoardV1[];
  storageIssue: BoardStorageIssue | null;
  canSave: boolean;
  isCreating: boolean;
  boardName: string;
  onBoardNameChange: (name: string) => void;
  onLoad: (board: BuiltInBoard | StoredBoardV1) => void;
  onStartCreating: () => void;
  onCancelCreating: () => void;
  onSave: () => void;
  onDelete: (id: string) => void;
  onClearStorage: () => void;
}


export function ComparisonBoardPicker({
  builtInBoards,
  customBoards,
  storageIssue,
  canSave,
  isCreating,
  boardName,
  onBoardNameChange,
  onLoad,
  onStartCreating,
  onCancelCreating,
  onSave,
  onDelete,
  onClearStorage,
}: ComparisonBoardPickerProps) {
  return (
    <section className="comparison-boards" aria-label="板块速选">
      <div className="comparison-section-heading">
        <div>
          <p className="eyebrow">BOARD PICKER</p>
          <h2>板块速选</h2>
        </div>
        <span>一键装载经过身份核验的组合；自定义板块仅保存在当前浏览器</span>
      </div>

      {storageIssue && (
        <div className="comparison-board-issue" role="status">
          <span>{storageIssue.message}</span>
          <button type="button" onClick={onClearStorage}>清除损坏存储</button>
        </div>
      )}

      <div className="comparison-board-grid">
        {builtInBoards.map((board) => (
          <article className="comparison-board-card comparison-board-card--built-in" key={board.id}>
            <button type="button" onClick={() => onLoad(board)}>
              <span className="comparison-board-card__title">
                <strong>{board.name}</strong>
                <small>{board.instruments.length} 个标的</small>
              </span>
              <span>{board.description}</span>
              <small>版本 {board.version} · 确认于 {board.confirmed_at}</small>
            </button>
          </article>
        ))}

        {customBoards.map((board) => (
          <article className="comparison-board-card" key={board.id}>
            <button type="button" onClick={() => onLoad(board)}>
              <span className="comparison-board-card__title">
                <strong>{board.name}</strong>
                <small>{board.instruments.length} 个标的</small>
              </span>
              <span>{board.instruments.map((item) => item.name).join("、")}</span>
              <small>本地自定义 · 存储版本 v{board.version}</small>
            </button>
            <button
              className="comparison-board-card__delete"
              type="button"
              aria-label={`删除自定义板块 ${board.name}`}
              onClick={() => onDelete(board.id)}
            >
              删除
            </button>
          </article>
        ))}

        <div className="comparison-board-create">
          {!isCreating ? (
            <button type="button" disabled={!canSave} onClick={onStartCreating}>
              <strong>保存当前组合</strong>
              <span>{canSave ? "创建本地自定义板块" : "选择至少 2 个标的后可保存"}</span>
            </button>
          ) : (
            <div className="comparison-board-create__form">
              <label htmlFor="comparison-board-name">板块名称</label>
              <input
                id="comparison-board-name"
                value={boardName}
                maxLength={30}
                placeholder="例如：我的宽基观察组"
                onChange={(event) => onBoardNameChange(event.target.value)}
              />
              <div>
                <button type="button" onClick={onSave}>保存</button>
                <button type="button" onClick={onCancelCreating}>取消</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
