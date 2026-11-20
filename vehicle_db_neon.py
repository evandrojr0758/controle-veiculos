"""PostgreSQL access for the vehicle app and its consumption screens."""

from types import SimpleNamespace

import psycopg
from psycopg import sql
from psycopg.types.json import Json

TABLES = {"veiculos", "movimentacoes", "consumo_relatorios"}
RPCS = {
    "corrigir_km_inicial_em_uso": ("p_movimentacao_id", "p_km_esperado", "p_novo_km"),
    "editar_cadastro_veiculo": ("p_placa_original", "p_placa", "p_modelo", "p_unidade", "p_atualizado_em"),
    "editar_cadastro_veiculo_com_foto": (
        "p_placa_original", "p_placa", "p_modelo", "p_unidade", "p_atualizado_em", "p_foto",
    ),
}


class NeonVehicles:
    def __init__(self, dsn):
        self.dsn = dsn

    def connect(self):
        return psycopg.connect(self.dsn, connect_timeout=10, prepare_threshold=None)

    def table(self, name):
        if name not in TABLES:
            raise ValueError("Tabela de veículos inválida.")
        return VehicleQuery(self, name)

    def rpc(self, name, params):
        fields = RPCS.get(name)
        if fields is None or set(params) != set(fields):
            raise ValueError("Operação de veículos inválida.")
        return VehicleRPC(self, name, [params[field] for field in fields])

    def start_trip(self, trip, revision_blocked):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT row_to_json(v.*) FROM public.veiculos v WHERE placa=%s FOR UPDATE",
                (trip["placa"],),
            ).fetchone()
            if row is None:
                raise ValueError("Veículo não encontrado. Atualize a tela.")
            if revision_blocked(row[0], trip["km_inicial"]):
                raise ValueError("VEÍCULO BLOQUEADO — REVISÃO URGENTE. Avise imediatamente à liderança.")
            if conn.execute(
                "SELECT 1 FROM public.movimentacoes WHERE placa=%s AND status='EM USO'",
                (trip["placa"],),
            ).fetchone():
                raise ValueError("Já existe uma saída em aberto para este veículo. Atualize a tela.")
            data = self.table("movimentacoes").insert(trip)._execute(conn)[0]
            conn.execute("UPDATE public.veiculos SET km_atual=%s, atualizado_em=%s WHERE placa=%s",
                         (trip["km_inicial"], trip["data_hora_saida"], trip["placa"]))
            return SimpleNamespace(data=[data])

    def finish_trip(self, placa, trip_id, km_inicial, km_final, returned_at):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT km_inicial FROM public.movimentacoes"
                " WHERE id=%s AND placa=%s AND status='EM USO' FOR UPDATE",
                (trip_id, placa),
            ).fetchone()
            if row is None:
                raise ValueError("A movimentação já foi encerrada ou não existe. Atualize a tela.")
            if row[0] != km_inicial:
                raise ValueError("O KM inicial mudou. Atualize a tela antes de devolver.")
            if km_final < row[0]:
                raise ValueError("O KM final deve ser igual ou maior que o KM inicial.")
            conn.execute(
                "UPDATE public.movimentacoes SET km_final=%s,data_hora_retorno=%s,status='DEVOLVIDO' WHERE id=%s",
                (km_final, returned_at, trip_id),
            )
            conn.execute("UPDATE public.veiculos SET km_atual=%s, atualizado_em=%s WHERE placa=%s",
                         (km_final, returned_at, placa))


class VehicleRPC:
    def __init__(self, db, name, values):
        self.db, self.name, self.values = db, name, values

    def execute(self):
        stmt = sql.SQL("SELECT public.{}({})").format(
            sql.Identifier(self.name), sql.SQL(", ").join(sql.Placeholder() for _ in self.values))
        try:
            with self.db.connect() as conn:
                return SimpleNamespace(data=conn.execute(stmt, self.values).fetchone()[0])
        except psycopg.errors.RaiseException as error:
            raise ValueError(error.diag.message_primary) from error


class VehicleQuery:
    def __init__(self, db, name):
        self.db = db
        self.target = sql.Identifier("public", name)
        self.operation = "select"
        self.fields = sql.SQL("*")
        self.filters, self.values, self.ordering = [], [], []
        self.row_limit = 1000
        self.payload = None

    def select(self, columns):
        if columns != "*":
            self.fields = sql.SQL(", ").join(sql.Identifier(c.strip()) for c in columns.split(","))
        return self

    def insert(self, data):
        self.operation, self.payload = "insert", data
        return self

    def update(self, data):
        self.operation, self.payload = "update", data
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, column, value):
        self.filters.append(sql.SQL("{} = %s").format(sql.Identifier(column)))
        self.values.append(value)
        return self

    def in_(self, column, values):
        if values:
            self.filters.append(sql.SQL("{} IN ({})").format(
                sql.Identifier(column), sql.SQL(", ").join(sql.Placeholder() for _ in values)))
            self.values.extend(values)
        else:
            self.filters.append(sql.SQL("FALSE"))
        return self

    def order(self, column, *, desc=False):
        self.ordering.append(sql.SQL("{} {}").format(sql.Identifier(column), sql.SQL("DESC" if desc else "ASC")))
        return self

    def limit(self, count):
        self.row_limit = min(self.row_limit, count)
        return self

    def execute(self):
        with self.db.connect() as conn:
            return SimpleNamespace(data=self._execute(conn))

    def _execute(self, conn):
        where = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(self.filters) if self.filters else sql.SQL("")
        if self.operation == "select":
            order = sql.SQL(" ORDER BY ") + sql.SQL(", ").join(self.ordering) if self.ordering else sql.SQL("")
            stmt = sql.SQL("SELECT {} FROM {}").format(self.fields, self.target) + where + order
            stmt = sql.SQL("SELECT row_to_json(v.*) FROM ({} LIMIT %s) v").format(stmt)
            return [r[0] for r in conn.execute(stmt, [*self.values, self.row_limit])]

        if self.operation in ("update", "delete") and not self.filters:
            raise ValueError("A alteração de veículos exige um filtro.")
        params = list(self.values)
        if self.operation == "delete":
            stmt = sql.SQL("DELETE FROM {}").format(self.target) + where
        else:
            columns = sql.SQL(", ").join(sql.Identifier(k) for k in self.payload)
            record = sql.SQL("SELECT {} FROM json_populate_record(NULL::{}, %s)").format(
                columns, self.target)
            if self.operation == "insert":
                stmt = sql.SQL("INSERT INTO {} ({}) ").format(self.target, columns) + record
            else:
                stmt = sql.SQL("UPDATE {} SET ({}) = ({})").format(self.target, columns, record) + where
            params.insert(0, Json(self.payload))
        query = sql.SQL("WITH v AS ({} RETURNING *) SELECT row_to_json(v.*) FROM v").format(stmt)
        return [r[0] for r in conn.execute(query, params)]
